"use strict";

const DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone";
const DEFAULT_MODEL = "jev-1.13.0";
const RETRYABLE_STATUSES = new Set([429, 529]);

class JevClientError extends Error {
  constructor(code, message, { status = null, retryable = false, cause = null } = {}) {
    super(message);
    this.name = "JevClientError";
    this.code = code;
    this.status = status;
    this.retryable = retryable;
    if (cause) this.cause = cause;
  }
}

function present(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function assertQuestions(questions) {
  if (!questions || typeof questions !== "object" || Array.isArray(questions)) {
    throw new JevClientError("questions_invalid", "Jev questions must be a non-empty object.");
  }
  const entries = Object.entries(questions);
  if (!entries.length) throw new JevClientError("questions_invalid", "Jev questions must be non-empty.");
  for (const [id, question] of entries) {
    if (!present(id) || !question || typeof question !== "object" || Array.isArray(question)) {
      throw new JevClientError("question_invalid", "A Jev question is malformed.");
    }
    if (!["noul", "choice", "score"].includes(question.type) || question.instructions == null) {
      throw new JevClientError("question_invalid", "A Jev question has an unsupported type or missing instructions.");
    }
    if (question.type === "choice") {
      if (!question.criteria || typeof question.criteria !== "object" || Array.isArray(question.criteria) || Object.keys(question.criteria).length < 2) {
        throw new JevClientError("question_invalid", "Choice questions require at least two criteria.");
      }
    }
    if (question.type === "score") {
      if (!Array.isArray(question.criteria) || question.criteria.length < 2 || question.criteria.length > 10) {
        throw new JevClientError("question_invalid", "Score questions require between two and ten criteria.");
      }
    }
  }
}

function finiteProbability(value) {
  return Number.isFinite(value) && value >= 0 && value <= 1;
}

function assertProbabilityMap(actual, expectedKeys) {
  if (!actual || typeof actual !== "object" || Array.isArray(actual)) {
    throw new JevClientError("provider_response_invalid", "Jev returned an invalid probability map.");
  }
  const actualKeys = Object.keys(actual).sort();
  const expected = [...expectedKeys].sort();
  if (JSON.stringify(actualKeys) !== JSON.stringify(expected)) {
    throw new JevClientError("provider_response_invalid", "Jev returned probability keys that do not match the request.");
  }
  let total = 0;
  for (const key of expected) {
    if (!finiteProbability(actual[key])) {
      throw new JevClientError("provider_response_invalid", "Jev returned an invalid probability.");
    }
    total += actual[key];
  }
  if (Math.abs(total - 1) > 1e-5) {
    throw new JevClientError("provider_response_invalid", "Jev probabilities do not sum to one.");
  }
}

function validateJevResponse(payload, questions, { expectedModel = null } = {}) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new JevClientError("provider_response_invalid", "Jev returned a malformed response.");
  }
  if (!present(payload.model) || !payload.answers || typeof payload.answers !== "object" || Array.isArray(payload.answers)) {
    throw new JevClientError("provider_response_invalid", "Jev response is missing model or answers.");
  }
  if (expectedModel && !expectedModel.endsWith("-latest") && !expectedModel.endsWith("-preview") && payload.model !== expectedModel) {
    throw new JevClientError("model_mismatch", "Jev returned a model different from the pinned model.");
  }

  const questionKeys = Object.keys(questions).sort();
  const answerKeys = Object.keys(payload.answers).sort();
  if (JSON.stringify(questionKeys) !== JSON.stringify(answerKeys)) {
    throw new JevClientError("provider_response_invalid", "Jev answers do not exactly match the requested questions.");
  }

  for (const id of questionKeys) {
    const question = questions[id];
    const answer = payload.answers[id];
    if (!answer || answer.type !== question.type) {
      throw new JevClientError("provider_response_invalid", "Jev returned an answer with the wrong type.");
    }
    if (question.type === "noul") {
      if (!finiteProbability(answer.noul)) {
        throw new JevClientError("provider_response_invalid", "Jev returned an invalid Noul value.");
      }
    } else if (question.type === "choice") {
      const options = Object.keys(question.criteria);
      if (!options.includes(answer.choice) || !finiteProbability(answer.confidence)) {
        throw new JevClientError("provider_response_invalid", "Jev returned an invalid Choice answer.");
      }
      assertProbabilityMap(answer.probabilities, options);
    } else if (question.type === "score") {
      if (!Number.isFinite(answer.score) || answer.score < 0 || answer.score > question.criteria.length - 1 || !finiteProbability(answer.confidence)) {
        throw new JevClientError("provider_response_invalid", "Jev returned an invalid Score answer.");
      }
      const levels = question.criteria.map((_, index) => String(index));
      assertProbabilityMap(answer.probabilities, levels);
      if (!answer.legend || typeof answer.legend !== "object" || Array.isArray(answer.legend)) {
        throw new JevClientError("provider_response_invalid", "Jev returned an invalid Score legend.");
      }
      for (const level of levels) {
        if (answer.legend[level] !== question.criteria[Number(level)]) {
          throw new JevClientError("provider_response_invalid", "Jev Score legend does not match the request.");
        }
      }
    }
  }

  const usage = payload.usage;
  if (!usage || !Number.isInteger(usage.input_tokens) || usage.input_tokens < 0 || !Number.isInteger(usage.output_tokens) || usage.output_tokens < 0) {
    throw new JevClientError("provider_response_invalid", "Jev response is missing valid usage counters.");
  }
  return payload;
}

function retryDelayMs(response, attempt) {
  const raw = response?.headers?.get?.("retry-after");
  if (raw) {
    const seconds = Number(raw);
    if (Number.isFinite(seconds) && seconds >= 0) return Math.min(seconds * 1000, 30000);
    const when = Date.parse(raw);
    if (Number.isFinite(when)) return Math.max(0, Math.min(when - Date.now(), 30000));
  }
  return Math.min(250 * (2 ** Math.max(0, attempt - 1)), 4000);
}

async function sleep(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function evaluateJev({
  state,
  questions,
  apiKey,
  model = DEFAULT_MODEL,
  endpoint = DEFAULT_ENDPOINT,
  timeoutMs = 15000,
  maxAttempts = 3,
  fetchImpl = globalThis.fetch,
  sleepImpl = sleep,
} = {}) {
  if (!present(apiKey)) throw new JevClientError("api_key_missing", "TypeSafe API key is not configured.");
  if (!present(model) || !present(endpoint)) throw new JevClientError("configuration_invalid", "Jev endpoint or model is invalid.");
  if (state == null || !["string", "object"].includes(typeof state)) {
    throw new JevClientError("state_invalid", "Jev state must be a string, object, or array.");
  }
  if (!Number.isInteger(maxAttempts) || maxAttempts < 1 || maxAttempts > 5) {
    throw new JevClientError("configuration_invalid", "Jev maxAttempts must be between one and five.");
  }
  if (typeof fetchImpl !== "function") throw new JevClientError("fetch_unavailable", "No fetch implementation is available.");
  assertQuestions(questions);

  const body = JSON.stringify({ state, model, questions });
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
      response = await fetchImpl(endpoint, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body,
        signal: controller.signal,
      });
    } catch (error) {
      clearTimeout(timeout);
      const code = error?.name === "AbortError" ? "provider_timeout" : "provider_transport_error";
      throw new JevClientError(code, "Jev request did not complete.", { cause: error });
    }
    clearTimeout(timeout);

    if (RETRYABLE_STATUSES.has(response.status) && attempt < maxAttempts) {
      await sleepImpl(retryDelayMs(response, attempt));
      continue;
    }
    if (!response.ok) {
      const retryable = RETRYABLE_STATUSES.has(response.status);
      throw new JevClientError(
        response.status === 401 ? "provider_unauthorized" : response.status === 422 ? "provider_request_rejected" : retryable ? "provider_retry_exhausted" : "provider_http_error",
        "Jev request failed.",
        { status: response.status, retryable },
      );
    }

    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw new JevClientError("provider_response_invalid", "Jev returned a non-JSON response.", { cause: error });
    }
    return validateJevResponse(payload, questions, { expectedModel: model });
  }
  throw new JevClientError("provider_retry_exhausted", "Jev retry budget was exhausted.", { retryable: true });
}

export {
  DEFAULT_ENDPOINT,
  DEFAULT_MODEL,
  JevClientError,
  evaluateJev,
  validateJevResponse,
};

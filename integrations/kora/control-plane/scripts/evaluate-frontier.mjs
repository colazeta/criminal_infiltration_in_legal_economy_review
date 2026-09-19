import { getInput, emitOutput } from "@kora/runtime-sdk";
import { evaluateFrontier } from "./frontier-core.mjs";

emitOutput(evaluateFrontier(getInput()));

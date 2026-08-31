"use strict";

import { DurableObject } from "cloudflare:workers";

import worker, { SubmissionCoordinatorCore } from "./index.js";

export class SubmissionCoordinator extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.core = new SubmissionCoordinatorCore(ctx, env);
  }

  fetch(request) {
    return this.core.fetch(request);
  }
}

export default worker;

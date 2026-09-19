import { getInput, emitOutput } from "@kora/runtime-sdk";
import { routeActivation } from "./router-core.mjs";

emitOutput(routeActivation(getInput()));

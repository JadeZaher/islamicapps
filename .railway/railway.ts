/** Railway Infrastructure as Code for the islamicapps service (converted from railway.json, 2026-11-22; conductor/RUNBOOK.md "Railway config conversion"). */
import { defineRailway, github, preserve, project, service } from "railway/iac";

// This repository manages only its own resources in the environment. Other
// repositories export their own partial name.
// See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "islamicapps";

export default defineRailway(() => {
  // Every setting railway.json carried, field for field (the generated conversion dropped the builder and the restart policy).
  // The start command is the Dockerfile's CMD and migrations are applied by hand: railway.json set neither, so neither is set here.
  const islamicapps = service("islamicapps", {
    // Deploys from main on every push, as before; the variables keep the values set in Railway (never written here).
    source: github("JadeZaher/islamicapps", { branch: "main" }),
    env: { DATABASE_URL: preserve(), NEXT_TELEMETRY_DISABLED: preserve(), SITE_URL: preserve() },
    build: { builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    deploy: {
      healthcheckPath: "/api/health",
      healthcheckTimeout: 120,
      // Railway stores its default (On Failure) as null, so `railway config plan` always lists this one line; the effective policy is On Failure.
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 5,
    },
  });
  return project("hadith-ontology", {
    resources: [islamicapps],
  });
});

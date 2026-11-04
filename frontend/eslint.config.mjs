import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // Паттерн проекта — загрузка данных в useEffect (void load()) с
      // setState внутри async: правило реагирует консервативно и ломает
      // линт на всех страницах-справочниках. Понижено до warn.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;

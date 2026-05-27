/**
 * @file ESLint configuration for ThemerrDB JavaScript tests and workflow helpers.
 */

import globals from "globals";
import pluginJs from "@eslint/js";

export default [
    pluginJs.configs.recommended,
    {
        ignores: [
            "coverage/**",
            "node_modules/**",
        ],
    },
    {
        languageOptions: {
            globals: {
                ...globals.node,
            },
        },
    },
];

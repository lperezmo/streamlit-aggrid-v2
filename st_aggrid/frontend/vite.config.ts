import react from "@vitejs/plugin-react";
import process from "node:process";
import { defineConfig, UserConfig } from "vite";

/**
 * Vite configuration for Streamlit AgGrid CCv2 component.
 */
export default defineConfig(() => {
  const isProd = process.env.NODE_ENV === "production";
  const isDev = !isProd;

  return {
    base: "./",
    publicDir: false, // Don't copy public/ files — CCv2 doesn't need them
    plugins: [react()],
    define: {
      "process.env.NODE_ENV": JSON.stringify(process.env.NODE_ENV),
    },
    css: {
      // Import CSS files normally
    },
    build: {
      minify: isDev ? false : "esbuild",
      outDir: "build",
      sourcemap: isDev,
      lib: {
        entry: "./src/index.tsx",
        name: "StreamlitAgGrid",
        formats: ["es"],
        fileName: "index-[hash]",
      },
      rollupOptions: {
        // Don't externalize anything — bundle everything for the component
        output: {
          assetFileNames: "index-[hash][extname]",
        },
      },
      ...(!isDev && {
        esbuild: {
          drop: ["debugger"],
          minifyIdentifiers: true,
          minifySyntax: true,
          minifyWhitespace: true,
        },
      }),
    },
  } satisfies UserConfig;
});

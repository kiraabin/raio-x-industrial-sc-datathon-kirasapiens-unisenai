// Copia os JSON gerados pelo backend (exportar.py) para public/data.
// Fonte única da verdade: data/processed/api. Nada de cálculo duplicado em JS.
import { cpSync, mkdirSync, existsSync, rmSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const dest = resolve(raiz, "frontend", "public", "data");
const api = resolve(raiz, "data", "processed", "api");
const geo = resolve(raiz, "data", "externos", "sc_municipios.geojson");

if (!existsSync(api)) {
  console.error("Falta " + api + ". Rode o backend (backend/exportar.py) primeiro.");
  process.exit(1);
}
rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
cpSync(api, dest, { recursive: true });
cpSync(geo, resolve(dest, "sc_municipios.geojson"));
console.log("dados sincronizados em", dest);

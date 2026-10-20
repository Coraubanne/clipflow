const { entrypoints } = require("uxp");
const ppro = require("premierepro");
const fs = require("fs");

// plugin-data:/ is Adobe's writable, per-plugin storage and requires no folder prompt.
const BRIDGE_ROOT = "plugin-data:/";
const IMPORTS_DIRECTORY = "plugin-data:/Imports";
const RESULTS_DIRECTORY = "plugin-data:/Results";
const ACTIVE_PROJECT_PATH = "plugin-data:/active-project.json";
let timer = null;
let busy = false;

function setStatus(state, title, detail) {
  document.body.dataset.state = state;
  const titleNode = document.getElementById("status");
  const detailNode = document.getElementById("project");
  if (titleNode) titleNode.textContent = title;
  if (detailNode) detailNode.textContent = detail;
}

async function ensureDirectories() {
  for (const directory of [IMPORTS_DIRECTORY, RESULTS_DIRECTORY]) {
    try {
      await fs.mkdir(directory, { recursive: true });
    } catch (error) {
      if (!String(error.message || error).toLowerCase().includes("exist")) throw error;
    }
  }
}

async function writeJson(target, payload) {
  await fs.writeFile(target, JSON.stringify(payload), { encoding: "utf-8" });
}

function childPath(directory, name) {
  return `${String(directory).replace(/\/$/, "")}/${name}`;
}

function fileStem(value) {
  return String(value).split("/").pop().replace(/\.json$/i, "");
}

function normalizedPath(value) {
  return String(value || "").replace(/\\/g, "/").replace(/\/+$/, "");
}

function samePath(first, second) {
  return normalizedPath(first) === normalizedPath(second);
}

async function writeProjectState(project) {
  await writeJson(ACTIVE_PROJECT_PATH, {
    projectPath: project.path,
    projectName: project.name,
    projectGuid: String(project.guid || ""),
    updatedAt: Date.now(),
  });
}

async function finishJob(jobPath, job, state, message) {
  const identifier = String(job.jobId || fileStem(jobPath));
  await writeJson(childPath(RESULTS_DIRECTORY, `${identifier}.json`), {
    state,
    message,
    updatedAt: Date.now(),
  });
  await fs.unlink(jobPath);
}

async function importNextJob(project) {
  const names = (await fs.readdir(IMPORTS_DIRECTORY))
    .filter((name) => name.endsWith(".json"))
    .sort();
  for (const name of names) {
    const jobPath = childPath(IMPORTS_DIRECTORY, name);
    let job;
    try {
      job = JSON.parse(await fs.readFile(jobPath, { encoding: "utf-8" }));
    } catch (error) {
      await finishJob(jobPath, {}, "error", `Demande ClipFlow invalide : ${error.message}`);
      continue;
    }
    if (!samePath(job.projectPath, project.path)) continue;
    try {
      const rootItem = await project.getRootItem();
      const imported = await project.importFiles([job.mediaPath], true, rootItem, false);
      if (!imported) throw new Error("Premiere Pro a refusé le fichier.");
      await finishJob(jobPath, job, "complete", "Média ajouté au projet Premiere Pro");
      setStatus("ready", "ClipFlow connecté", `${project.name} · média importé`);
    } catch (error) {
      await finishJob(jobPath, job, "error", String(error.message || error));
      setStatus("error", "Import impossible", String(error.message || error));
    }
    break;
  }
}

async function tick() {
  if (busy) return;
  busy = true;
  try {
    await ensureDirectories();
    const project = await ppro.Project.getActiveProject();
    if (!project || !project.path || !String(project.path).toLowerCase().endsWith(".prproj")) {
      setStatus("waiting", "Projet non enregistré", "Enregistrez le projet pour activer ClipFlow.");
      return;
    }
    await writeProjectState(project);
    setStatus("ready", "ClipFlow connecté", project.name || project.path);
    await importNextJob(project);
  } catch (error) {
    console.log(`[ClipFlow] Erreur : ${String(error.message || error)}`);
    setStatus("error", "ClipFlow indisponible", String(error.message || error));
  } finally {
    busy = false;
  }
}

function startBridge() {
  if (timer !== null) return;
  tick();
  timer = setInterval(tick, 1000);
}

function stopBridge() {
  if (timer === null) return;
  clearInterval(timer);
  timer = null;
}

entrypoints.setup({
  plugin: {
    create() {
      startBridge();
    },
    destroy() {
      stopBridge();
    },
  },
  panels: {
    clipflowBridge: {
      create() {
        startBridge();
      },
      show() {
        startBridge();
        tick();
      },
      destroy() {
        stopBridge();
      },
    },
  },
});

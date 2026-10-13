"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function openDemo() {
  const html = fs.readFileSync(path.join(__dirname, "..", "web", "index.html"), "utf8");
  const script = html.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(script, "Expected inline rules demonstration code");
  const fields = {
    "task_id": { value: "DEMO-001" },
    "target_id": { value: "SAMPLE-001" },
    "primary_metric": { value: "29.4" },
    "secondary_metric": { value: "14.8" },
    "status_descriptor": { value: "DISCORDANT_ANOMALY" },
    "is_critical": { checked: true },
    "m-status": { textContent: "Not run" },
    "m-tasks": { textContent: "0" },
    "outputConsole": { textContent: "" },
    "error": { textContent: "" },
    "export-btn": { disabled: true },
    "audit-form": {},
    "sample-btn": {}
  };
  for (const element of Object.values(fields)) {
    element.listeners = {};
    element.addEventListener = (type, handler) => { element.listeners[type] = handler; };
  }
  const downloads = [];
  const document = {
    getElementById: (id) => fields[id],
    createElement: (tag) => {
      assert.equal(tag, "a");
      const element = { download: "", href: "", click() {
        downloads.push({ filename: this.download, href: this.href });
      }, remove() {} };
      return element;
    },
    body: { appendChild() {} }
  };
  const urls = [];
  const URL = {
    createObjectURL(blob) {
      const address = "blob:example-" + urls.length;
      urls.push(blob);
      return address;
    },
    revokeObjectURL() {}
  };
  class Blob {
    constructor(parts, options) {
      this.parts = parts;
      this.type = options.type;
    }
  }
  vm.runInNewContext(script[1], { document, URL, Blob, console }, { timeout: 1000 });
  const submit = () => fields["audit-form"].listeners.submit({preventDefault() {}});
  return { fields, downloads, urls, submit };
}

test("normal rule evaluation is explicit, deterministic and exportable", () => {
  const demo = openDemo();
  const f = demo.fields;
  demo.submit();
  const result = JSON.parse(f.outputConsole.textContent);
  assert.equal(result.mode, "BROWSER_RULE_DEMO");
  assert.equal(result.overall_urgency, "CRITICAL_STAT_PANIC");
  assert.equal(result.total_alerts, 3);
  assert.equal(result.critical_alerts_count, 1);
  assert.equal(result.audit_hash, null);
  assert.equal(result.clinical_classification, null);
  assert.equal(f["m-tasks"].textContent, "1");
  assert.equal(f["export-btn"].disabled, false);
  f["export-btn"].listeners.click();
  assert.equal(demo.downloads[0].filename, "endoscopy-rule-evaluation.json");
  assert.equal(demo.urls[0].type, "application/json");
  assert.equal(JSON.parse(demo.urls[0].parts[0]).total_alerts, 3);
});

test("routine, elevated and invalid input handling", () => {
  const demo = openDemo();
  const f = demo.fields;
  f.primary_metric.value = "1";
  f.secondary_metric.value = "1";
  f.status_descriptor.value = "NOMINAL";
  f.is_critical.checked = false;
  demo.submit();
  assert.equal(JSON.parse(f.outputConsole.textContent).overall_urgency, "ROUTINE");
  f.primary_metric.value = "26";
  demo.submit();
  assert.equal(JSON.parse(f.outputConsole.textContent).overall_urgency, "ELEVATED_RISK");
  assert.equal(f["m-tasks"].textContent, "2");
  f.primary_metric.value = "";
  demo.submit();
  assert.match(f.error.textContent, /finite/);
  assert.equal(f["m-tasks"].textContent, "2");
  f.primary_metric.value = "1";
  f.task_id.value = "MRN-12345678";
  demo.submit();
  assert.match(f.error.textContent, /patient information/);
  assert.equal(f["m-tasks"].textContent, "2");
});

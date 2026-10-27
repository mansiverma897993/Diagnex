import { jsPDF } from "jspdf";
import fs from "node:fs";

// Generate the PDF from SYNOPSIS.md so the two documents cannot drift apart.
const source = fs.readFileSync(new URL("./SYNOPSIS.md", import.meta.url), "utf8");
const doc = new jsPDF({ unit: "mm", format: "a4" });
const margin = 17;
const width = 210 - 2 * margin;
let y = 20;

function space(height) {
  if (y + height > 278) {
    doc.addPage();
    y = 20;
  }
}

function print(text, size = 10, bold = false, color = [30, 41, 59], gap = 2.5) {
  doc.setFont("helvetica", bold ? "bold" : "normal");
  doc.setFontSize(size);
  doc.setTextColor(...color);
  const lines = doc.splitTextToSize(text, width);
  const lineHeight = size * 0.46;
  space(lines.length * lineHeight + gap);
  doc.text(lines, margin, y);
  y += lines.length * lineHeight + gap;
}

for (const rawLine of source.split(/\r?\n/)) {
  const line = rawLine.trim();
  if (!line) {
    y += 2;
    continue;
  }
  if (line.startsWith("# ")) {
    print(line.slice(2), 19, true, [30, 58, 138], 5);
  } else if (line.startsWith("## ")) {
    print(line.slice(3), 12, true, [30, 58, 138], 4);
  } else if (line.startsWith("|")) {
    if (/^\|\s*:?-+/.test(line)) continue;
    const cells = line.split("|").slice(1, -1).map((cell) => cell.trim().replaceAll("**", ""));
    print(cells.join("    "), 8.5, false, [30, 41, 59], 1.5);
  } else {
    print(line.replaceAll("**", "").replaceAll(/\[([^\]]+)\]\([^)]*\)/g, "$1"), 9.5);
  }
}

const outPath = new URL("./SYNOPSIS.pdf", import.meta.url);
fs.writeFileSync(outPath, doc.output(), "binary");
console.log(`PDF written to ${outPath.pathname}; ${doc.getNumberOfPages()} page(s)`);

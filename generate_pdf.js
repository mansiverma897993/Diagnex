import { jsPDF } from 'jspdf';
import fs from 'node:fs';

// SYNOPSIS.md is the source of truth for this one-page PDF.
const markdown = fs.readFileSync(new URL('./SYNOPSIS.md', import.meta.url), 'utf8');
const sections = [];
const meta = [];
let title = '';
let current = null;
for (const raw of markdown.split(/\r?\n/)) {
  const line = raw.trim();
  if (!line) continue;
  if (line.startsWith('# ')) title = line.slice(2);
  else if (line.startsWith('> ')) meta.push(line.slice(2));
  else if (line.startsWith('## ')) {
    current = { name: line.slice(3), lines: [] };
    sections.push(current);
  } else if (current) current.lines.push(line);
}

const doc = new jsPDF({ unit: 'mm', format: 'a4', compress: true });
doc.setProperties({
  title: `${title} | Project Synopsis`,
  author: 'Mansi Verma',
  subject: 'Research prototype for medical visual question answering',
  keywords: 'Diagnex, medical VQA, project synopsis',
});
const navy = [20, 43, 69];
const teal = [0, 126, 145];
const ink = [36, 49, 61];
const muted = [91, 107, 119];
const pale = [242, 247, 249];
const left = 17;
const right = 193;
const width = right - left;
let y = 54;

const plain = (s) => s.replace(/\*\*/g, '').replace(/`/g, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1');

function setFont(size, bold = false, color = ink) {
  doc.setFont('helvetica', bold ? 'bold' : 'normal');
  doc.setFontSize(size);
  doc.setTextColor(...color);
}

function wrapped(text, x, availableWidth, size = 8.9, leading = 4.0, color = ink) {
  setFont(size, false, color);
  const lines = doc.splitTextToSize(plain(text), availableWidth);
  doc.text(lines, x, y);
  y += lines.length * leading;
}

function sectionHeading(name) {
  y += 2.1;
  setFont(9.8, true, teal);
  doc.text(name.toUpperCase(), left, y);
  doc.setDrawColor(206, 221, 227);
  doc.setLineWidth(0.25);
  doc.line(left, y + 1.8, right, y + 1.8);
  y += 7.0;
}

function bullet(text) {
  doc.setFillColor(...teal);
  doc.circle(left + 1.3, y - 1.0, 0.6, 'F');
  wrapped(text, left + 4.5, width - 4.5);
  y += 0.8;
}

function numbered(text) {
  const match = text.match(/^(\d+)\.\s+(.*)$/);
  if (!match) return;
  setFont(8.9, true, teal);
  doc.text(`${match[1]}.`, left, y);
  wrapped(match[2], left + 5.2, width - 5.2);
  y += 0.8;
}

function table(lines) {
  const rows = lines.filter((line) => line.startsWith('|')).map((line) =>
    line.split('|').slice(1, -1).map((cell) => plain(cell.trim())))
    .filter((cells) => cells.length === 2 && !/^:?-+:?$/.test(cells[0]));
  const rowH = 6.7;
  rows.forEach(([measure, result], i) => {
    const top = y - 3.5;
    doc.setFillColor(...(i === 0 ? navy : i % 2 === 0 ? pale : [255, 255, 255]));
    doc.rect(left, top, width, rowH, 'F');
    setFont(i === 0 ? 8.5 : 8.7, i === 0, i === 0 ? [255, 255, 255] : ink);
    doc.text(measure, left + 2.5, y);
    doc.text(result, right - 2.5, y, { align: 'right' });
    y += rowH;
  });
  y += 0.7;
}

// Formal title block.
doc.setFillColor(...navy);
doc.rect(0, 0, 210, 47, 'F');
doc.setFillColor(...teal);
doc.rect(0, 0, 5, 47, 'F');
setFont(8.5, true, [169, 222, 229]);
doc.text('B.TECH FINAL-YEAR PROJECT  /  PROJECT SYNOPSIS', left, 11.5);
setFont(24, true, [255, 255, 255]);
doc.text(title, left, 24.5);
setFont(10.2, false, [224, 236, 242]);
doc.text('Medical visual question answering with calibrated abstention', left, 32);
setFont(8.0, false, [224, 236, 242]);
doc.text(meta[0], left, 38.2);
doc.text(meta[1], left, 43.0);

for (const section of sections) {
  sectionHeading(section.name);
  if (section.name === 'Held-out results') {
    table(section.lines);
    continue;
  }
  for (const line of section.lines) {
    if (line.startsWith('- ')) bullet(line.slice(2));
    else if (/^\d+\.\s+/.test(line)) numbered(line);
    else if (line.startsWith('Source of results:')) {
      y += 0.7;
      wrapped(line, left, width, 7.5, 3.3, muted);
    } else {
      wrapped(line, left, width);
      y += 0.8;
    }
  }
}

if (y > 278) throw new Error(`Synopsis overflows one page: content ends at ${y.toFixed(1)} mm`);
doc.setDrawColor(206, 221, 227);
doc.line(left, 282, right, 282);
setFont(7.7, false, muted);
doc.text('DIAGNEX  |  Research prototype; not for clinical diagnosis', left, 287);
doc.text('1 / 1', right, 287, { align: 'right' });

const out = new URL('./SYNOPSIS.pdf', import.meta.url);
fs.writeFileSync(out, doc.output(), 'binary');
console.log(`Created ${out.pathname}; ${doc.getNumberOfPages()} page; content ends at ${y.toFixed(1)} mm`);

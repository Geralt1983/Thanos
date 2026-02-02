#!/usr/bin/env node
/**
 * Format Epic contract opportunities as email
 * Usage: node format-epic-email.js [dataset-id]
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const datasetId = process.argv[2] || 'qyiHMt37jhYd6b10V';

// Persistent seen file (shared with scraper)
const SEEN_FILE = path.join(__dirname, '../data/linkedin-seen-posts.json');

function loadSeenPosts() {
  try {
    return JSON.parse(fs.readFileSync(SEEN_FILE, 'utf8'));
  } catch { return {}; }
}

function saveSeenPosts(seen) {
  fs.writeFileSync(SEEN_FILE, JSON.stringify(seen, null, 2));
}

// Priority modules (shown first)
const PRIORITY_MODULES = ['Orders', 'ClinDoc', 'Inpatient'];

// All modules for detection
const MODULES = [
  'Orders', 'ClinDoc', 'ASAP', 'Ambulatory', 'Beaker', 'Beacon',
  'Bridges', 'Caboodle', 'Cadence', 'Cogito', 'Cupid', 'MyChart', 'Optime',
  'Prelude', 'Radiant', 'Resolute', 'Clarity', 'Tapestry', 
  'Revenue Cycle', 'PB', 'HB', 'Grand Central', 'Compass Rose', 'Referrals',
  'Healthy Planet', 'Stork', 'Home Health', 'Wisdom', 'Kaleidoscope',
  // Willow variants (check longer strings first)
  'Willow Inpatient', 'Willow Ambulatory', 'Willow Inventory', 'Willow',
  // Inpatient (check after Willow Inpatient)
  'Inpatient'
];

// Epic keywords
const DEFINITIVE_EPIC = [
  'mychart', 'beaker', 'clindoc', 'caboodle', 'cogito', 'willow',
  'cadence', 'prelude', 'resolute', 'optime', 'hyperspace', 'care everywhere',
  'epic orders', 'epic inpatient', 'epic ambulatory', 'epic radiant', 'epic asap',
  'epic bridges', 'epic stork', 'epic cupid', 'epic beacon', 'epic tapestry',
  'epic clarity', 'epic reporting', 'epic revenue', 'epic pb', 'epic hb',
  'epic certified', 'epic certification', 'epic analyst', 'epic consultant',
  'epic go-live', 'epic implementation', 'epic build', 'epic trainer',
  'epic support', 'epic ehr', 'epic emr', 'epic systems'
];

const JOB_PHRASES = [
  'now hiring', "we're hiring", 'we are hiring', '#hiring', 'i am hiring',
  "we're looking for", 'we are looking for', "i'm looking for", 'i am looking for',
  "we're seeking", 'we are seeking', 'seeking a certified', 'seeking an epic', 'i am seeking',
  'apply today', 'apply now', 'send your resume', 'send resume', 'email your resume',
  'dm me', 'dm for details', 'reach out if', 'reach out to',
  'contract opportunity', 'contract position', 'contract role', 'contract need', 'contract needs',
  'contract openings', 'contracts available', 'epic contract', 'epic contracts',
  'immediate need', 'urgent need', 'hot requirement', 'new opportunity', 'open position',
  'job opportunity', 'epic certified', 'epic certification required', 'certification required',
  'currently seeking', 'we are needing', 'i am needing', 'opportunities available'
];

const CONTRACT = ['contract', 'consultant', 'consulting', 'c2c', 'w2', '1099', 'month', 'duration'];

function isRecent(p) {
  const t = p.timeSincePosted || '';
  if (t.includes('mo') || t.includes('y')) return false;
  const w = t.match(/(\d+)\s*w/);
  if (w && parseInt(w[1]) > 1) return false;
  return true;
}

const EPIC_MODULES_CHECK = [
  'orders', 'clindoc', 'inpatient', 'ambulatory', 'beaker', 'radiant', 'willow',
  'cadence', 'prelude', 'resolute', 'optime', 'mychart', 'caboodle', 'cogito',
  'bridges', 'beacon', 'tapestry', 'stork', 'cupid', 'clarity', 'asap',
  'revenue cycle', 'grand central', 'adt', 'hb', 'pb', 'healthy planet',
  'compass rose', 'referrals', 'home health', 'wisdom', 'kaleidoscope'
];

const EPIC_POSITIONS = [
  'analyst', 'consultant', 'trainer', 'builder', 'developer', 'architect',
  'project manager', 'implementation', 'support', 'certified'
];

function hasEpic(text) {
  const l = text.toLowerCase();
  
  if (DEFINITIVE_EPIC.some(k => l.includes(k))) return true;
  
  // "epic contract(s)" needs module or position
  if (l.includes('epic contract')) {
    return EPIC_MODULES_CHECK.some(m => l.includes(m)) || EPIC_POSITIONS.some(p => l.includes(p));
  }
  
  return false;
}

function hasJob(text) {
  const l = text.toLowerCase();
  if (!JOB_PHRASES.some(p => l.includes(p))) return false;
  return CONTRACT.some(k => l.includes(k));
}

function getMods(text) {
  const l = text.toLowerCase();
  const found = [];
  const used = new Set();
  
  // Check longer module names first to avoid partial matches
  const sorted = [...MODULES].sort((a, b) => b.length - a.length);
  
  for (const m of sorted) {
    const ml = m.toLowerCase();
    if (l.includes(ml)) {
      // Don't add "Willow" if we already have "Willow Inpatient", etc.
      // Don't add "Inpatient" if we already have "Willow Inpatient"
      const dominated = found.some(f => f.toLowerCase().includes(ml));
      if (!dominated) {
        found.push(m);
      }
    }
  }
  return found;
}

function getDetails(text) {
  const l = text.toLowerCase();
  const d = [];
  
  // Duration
  const dur = text.match(/(\d+)[\s-]*(month|week|year)/i);
  if (dur) d.push(dur[0].replace('-', ' '));
  
  // Location
  if (l.includes('100% remote') || l.includes('fully remote')) d.push('100% Remote');
  else if (l.includes('remote')) d.push('Remote');
  if (l.includes('onsite') || l.includes('on-site')) d.push('Onsite');
  if (l.includes('hybrid')) d.push('Hybrid');
  
  // Contract type
  if (l.includes('c2c') || l.includes('corp to corp')) d.push('C2C');
  if (l.includes('w2')) d.push('W2');
  if (l.includes('1099')) d.push('1099');
  
  // Experience
  const exp = text.match(/(\d+)\+?\s*(?:years?|yrs?)/i);
  if (exp && l.includes('experience')) d.push(`${exp[1]}+ yrs`);
  
  // Start
  if (l.includes('asap') || l.includes('immediate')) d.push('ASAP');
  
  // Certification
  if (l.includes('certified') || l.includes('certification')) d.push('Cert Req');
  
  // Rate (if mentioned)
  const rate = text.match(/\$(\d{2,3})(?:\/hr|\/hour| per hour| hourly)?/i);
  if (rate) d.push(`$${rate[1]}/hr`);
  
  return d.join(' • ') || 'See post';
}

// Known staffing firms
const STAFFING_FIRMS = [
  'Walker Healthforce', 'Divurgent', 'Nordic', 'Pivot Point', 'Health Catalyst',
  'Tegria', 'Impact Advisors', 'Prominence', 'Optimum Healthcare IT', 'Chartis',
  'Huron', 'Hayes Management', 'Leidos', 'Accenture', 'Deloitte', 'Slalom',
  'Avanade', 'Cognizant', 'Pride Health', 'Cardamom', 'ViRTELLIGENCE',
  'Healthtech Solutions', 'CereCore', 'MEDHOST', 'Prominence Advisors',
  'ROI Healthcare', 'Stoltenberg', 'Galen Healthcare', 'Bluetree', 'Core Solutions',
  'Walker Healthforce', 'Contech', 'Ernst & Young', 'CTG Health', 'Quartet AI', 'QuartetAI'
];

// Map variations to canonical names
const FIRM_ALIASES = {
  'quartetai': 'Quartet AI',
  'quartet ai': 'Quartet AI',
  'sgs consulting': 'SGS Consulting',
  'empower professional': 'Empower Professionals',
};

function getFirm(text, authorHeadline) {
  const combined = `${text} ${authorHeadline || ''}`.toLowerCase();
  
  // Check aliases first
  for (const [alias, canonical] of Object.entries(FIRM_ALIASES)) {
    if (combined.includes(alias)) return canonical;
  }
  
  // Check staffing firms
  for (const firm of STAFFING_FIRMS) {
    if (combined.includes(firm.toLowerCase())) {
      return firm;
    }
  }
  
  // Try to extract from headline (e.g., "Recruiter at XYZ Health")
  if (authorHeadline) {
    const atMatch = authorHeadline.match(/(?:at|@)\s+([A-Z][A-Za-z\s]+(?:Health|IT|Solutions|Consulting)?)/i);
    if (atMatch) return atMatch[1].trim();
  }
  return null;
}

function getSummary(text) {
  if (!text) return '';
  // Clean up the text
  let clean = text
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/^[\s🚨📍💻✔️🔹📅⭐🔧📋👤🔗#]+/, '')
    .trim();
  
  // Extract first 1-2 meaningful sentences (up to 150 chars)
  const sentences = clean.split(/(?<=[.!?])\s+/);
  let summary = '';
  for (const s of sentences) {
    if (summary.length + s.length > 150) break;
    summary += (summary ? ' ' : '') + s;
  }
  return summary || clean.substring(0, 150) + '...';
}

function hasPriorityModule(mods) {
  return PRIORITY_MODULES.some(pm => mods.includes(pm));
}

async function main() {
  const result = execSync(`apify datasets get-items ${datasetId} --format=json`, 
    { maxBuffer: 100 * 1024 * 1024 }).toString();
  const jsonStart = result.indexOf('[');
  const posts = JSON.parse(result.slice(jsonStart));

  // Filter
  let filtered = posts.filter(p => p.text && isRecent(p) && hasEpic(p.text) && hasJob(p.text));

  // Normalize URL for dedup
  function normalizeUrl(url) {
    if (!url) return null;
    try {
      const u = new URL(url);
      u.searchParams.delete('rcm');
      u.searchParams.delete('utm_source');
      u.searchParams.delete('utm_medium');
      return u.toString();
    } catch { return url; }
  }

  // Load previously seen posts
  const seenPosts = loadSeenPosts();
  const now = Date.now();

  // Dedup within batch AND against previously emailed
  const batchSeen = new Set();
  filtered = filtered.filter(p => {
    const key = normalizeUrl(p.url);
    // Skip if in this batch already
    if (batchSeen.has(key)) return false;
    batchSeen.add(key);
    // Skip if previously emailed
    if (seenPosts[key]) return false;
    return true;
  });

  // Mark all as seen for next run
  filtered.forEach(p => {
    const key = normalizeUrl(p.url);
    seenPosts[key] = now;
  });
  
  // Prune old entries (>30 days)
  const cutoff = now - (30 * 24 * 60 * 60 * 1000);
  for (const [k, v] of Object.entries(seenPosts)) {
    if (v < cutoff) delete seenPosts[k];
  }
  saveSeenPosts(seenPosts);

  // Add modules, firm, summary to each
  filtered = filtered.map(p => ({
    ...p,
    modules: getMods(p.text),
    details: getDetails(p.text),
    firm: getFirm(p.text, p.authorHeadline),
    summary: getSummary(p.text),
    hasPriority: hasPriorityModule(getMods(p.text))
  }));

  // Sort: priority modules first, then by recency
  filtered.sort((a, b) => {
    if (a.hasPriority && !b.hasPriority) return -1;
    if (!a.hasPriority && b.hasPriority) return 1;
    return 0;
  });

  // Build summary
  const moduleCounts = {};
  filtered.forEach(p => {
    p.modules.forEach(m => {
      moduleCounts[m] = (moduleCounts[m] || 0) + 1;
    });
  });

  const priorityCount = filtered.filter(p => p.hasPriority).length;
  const otherCount = filtered.length - priorityCount;

  // Output
  const date = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
  
  console.log(`Subject: Epic Contract Digest - ${date}\n`);
  console.log(`SUMMARY`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`${filtered.length} opportunities this week`);
  console.log(`⭐ ${priorityCount} in Orders/ClinDoc/Inpatient`);
  console.log(`📋 ${otherCount} in other modules\n`);
  
  // Top modules
  const topMods = Object.entries(moduleCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([m, c]) => `${m}: ${c}`)
    .join(' | ');
  console.log(`Hot modules: ${topMods}\n`);
  
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`);

  // Priority section
  if (priorityCount > 0) {
    console.log(`⭐ ORDERS / CLINDOC / INPATIENT\n`);
    filtered.filter(p => p.hasPriority).forEach(p => {
      const header = p.firm ? `${p.authorName || 'Unknown'} @ ${p.firm}` : (p.authorName || 'Unknown');
      console.log(`▸ ${header}`);
      if (p.modules.length) console.log(`  Modules: ${p.modules.slice(0, 5).join(', ')}`);
      console.log(`  Details: ${p.details}`);
      if (p.summary) console.log(`  "${p.summary}"`);
      console.log(`  ${p.url}\n`);
    });
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`);
  }

  // Other section
  if (otherCount > 0) {
    console.log(`📋 OTHER MODULES\n`);
    filtered.filter(p => !p.hasPriority).forEach(p => {
      const header = p.firm ? `${p.authorName || 'Unknown'} @ ${p.firm}` : (p.authorName || 'Unknown');
      console.log(`▸ ${header}`);
      if (p.modules.length) console.log(`  Modules: ${p.modules.slice(0, 5).join(', ')}`);
      console.log(`  Details: ${p.details}`);
      if (p.summary) console.log(`  "${p.summary}"`);
      console.log(`  ${p.url}\n`);
    });
  }

  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`Generated by Thanos • ${new Date().toLocaleString()}`);
}

main().catch(e => console.error(e.message));

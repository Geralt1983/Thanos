#!/usr/bin/env node
/**
 * Process existing Apify dataset for Epic contract opportunities
 * Usage: node process-linkedin-epic.js <dataset-id> [--no-dedup]
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const datasetId = process.argv[2] || 'qyiHMt37jhYd6b10V';
const skipDedup = process.argv.includes('--no-dedup');

// Persistent dedup file
const SEEN_FILE = path.join(__dirname, '../data/linkedin-seen-posts.json');

// Definitive Epic keywords (unique to Epic EHR - no false positives)
const DEFINITIVE_EPIC = [
  // Unique module names (unmistakable)
  'mychart', 'beaker', 'clindoc', 'caboodle', 'cogito', 'willow',
  'cadence', 'prelude', 'resolute', 'optime', 'hyperspace', 'care everywhere',
  // Epic + module compounds
  'epic orders', 'epic inpatient', 'epic ambulatory', 'epic radiant', 'epic asap',
  'epic bridges', 'epic stork', 'epic cupid', 'epic beacon', 'epic tapestry',
  'epic clarity', 'epic reporting', 'epic revenue', 'epic pb', 'epic hb',
  // Epic + role/action (healthcare-specific)
  'epic certified', 'epic certification', 'epic analyst', 'epic consultant',
  'epic go-live', 'epic implementation', 'epic build', 'epic trainer',
  'epic support', 'epic ehr', 'epic emr', 'epic systems'
];

// Strong job-posting phrases (require at least one)
const JOB_PHRASES = [
  'now hiring', 'we\'re hiring', 'we are hiring', '#hiring', 'i am hiring',
  'we\'re looking for', 'we are looking for', 'i\'m looking for', 'i am looking for',
  'we\'re seeking', 'we are seeking', 'seeking a certified', 'seeking an epic', 'i am seeking',
  'apply today', 'apply now', 'send your resume', 'send resume', 'email your resume',
  'dm me', 'dm for details', 'reach out if', 'reach out to',
  'contract opportunity', 'contract position', 'contract role', 'contract need', 'contract needs',
  'contract openings', 'contracts available', 'epic contract', 'epic contracts',
  'immediate need', 'urgent need', 'hot requirement', 'new opportunity', 'open position',
  'job opportunity', 'epic certified', 'epic certification required', 'certification required',
  'currently seeking', 'we are needing', 'i am needing', 'opportunities available'
];

// Contract indicators
const CONTRACT_KEYWORDS = [
  'contract', 'consultant', 'consulting', 'c2c', 'corp to corp', 'w2', '1099',
  'month contract', 'remote contract', 'months', 'start date', 'duration'
];

// Exclude (unless informatics)
const EXCLUDE = ['registered nurse rn', 'lpn position', 'cna position', 'physician assistant'];

// Epic modules
const MODULES = [
  'Orders', 'Inpatient', 'ClinDoc', 'ASAP', 'Ambulatory', 'Beaker',
  'Bridges', 'Caboodle', 'Cadence', 'Cogito', 'Cupid', 'Healthy Planet',
  'HIM', 'MyChart', 'Optime', 'Prelude', 'Radiant', 'Resolute', 'Revenue Cycle',
  'Stork', 'Tapestry', 'Willow', 'Wisdom', 'Grand Central', 'ADT', 'Clarity'
];

// Staffing firms
const FIRMS = [
  'Divurgent', 'Nordic', 'Pivot Point', 'Health Catalyst', 'Tegria',
  'Impact Advisors', 'Prominence', 'Optimum', 'Huron', 'Leidos',
  'Accenture', 'Deloitte', 'Slalom', 'Cognizant',
  'Pride Health', 'Cardamom', 'ViRTELLIGENCE', 'CereCore', 'Contech',
  'Walker Healthforce', 'Ernst & Young', 'CTG Health'
];

// --- Helpers ---

function loadSeenPosts() {
  try {
    if (fs.existsSync(SEEN_FILE)) {
      const data = JSON.parse(fs.readFileSync(SEEN_FILE, 'utf8'));
      const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
      const filtered = {};
      for (const [key, ts] of Object.entries(data)) {
        if (ts > cutoff) filtered[key] = ts;
      }
      return filtered;
    }
  } catch (e) { /* ignore */ }
  return {};
}

function saveSeenPosts(seen) {
  const dir = path.dirname(SEEN_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(SEEN_FILE, JSON.stringify(seen, null, 2));
}

function getPostKey(post) {
  return post.url || post.urn || (post.text || '').substring(0, 150);
}

function isRecent(post) {
  const timeStr = post.timeSincePosted || '';
  if (timeStr.includes('mo') || timeStr.includes('month')) return false;
  if (timeStr.includes('y') || timeStr.includes('year')) return false;
  const weekMatch = timeStr.match(/(\d+)\s*w/);
  if (weekMatch && parseInt(weekMatch[1]) > 1) return false;
  return true;
}

// Module/position names that confirm Epic EHR context
const EPIC_MODULES_CHECK = [
  'orders', 'clindoc', 'inpatient', 'ambulatory', 'beaker', 'radiant', 'willow',
  'cadence', 'prelude', 'resolute', 'optime', 'mychart', 'caboodle', 'cogito',
  'bridges', 'beacon', 'tapestry', 'stork', 'cupid', 'clarity', 'asap',
  'revenue cycle', 'grand central', 'adt', 'hb', 'pb', 'healthy planet'
];

const EPIC_POSITIONS = [
  'analyst', 'consultant', 'trainer', 'builder', 'developer', 'architect',
  'project manager', 'implementation', 'support', 'certified'
];

function hasEpicKeyword(text) {
  const lower = text.toLowerCase();
  
  // Definitive keywords
  if (DEFINITIVE_EPIC.some(kw => lower.includes(kw))) return true;
  
  // "epic contract(s)" needs module or position
  if (lower.includes('epic contract')) {
    const hasModule = EPIC_MODULES_CHECK.some(m => lower.includes(m));
    const hasPosition = EPIC_POSITIONS.some(p => lower.includes(p));
    return hasModule || hasPosition;
  }
  
  return false;
}

function hasContractKeyword(text) {
  const lower = text.toLowerCase();
  
  // Must have a job-posting phrase
  if (!JOB_PHRASES.some(phrase => lower.includes(phrase))) return false;
  
  // Should also have contract indicators
  return CONTRACT_KEYWORDS.some(kw => lower.includes(kw));
}

function shouldExclude(text) {
  const lower = text.toLowerCase();
  if (lower.includes('informatics')) return false;
  return EXCLUDE.some(kw => lower.includes(kw));
}

function extractModules(text) {
  const found = [];
  const lower = text.toLowerCase();
  for (const mod of MODULES) {
    if (lower.includes(mod.toLowerCase())) found.push(mod);
  }
  return found.length ? found : ['General'];
}

function extractFirm(post, text) {
  const fullText = `${text} ${post.authorName || ''} ${post.authorHeadline || ''}`.toLowerCase();
  for (const firm of FIRMS) {
    if (fullText.includes(firm.toLowerCase())) return firm;
  }
  return post.authorName || 'Unknown';
}

function extractDetails(text) {
  const details = [];
  const lower = text.toLowerCase();
  
  const duration = text.match(/(\d+)\s*(month|week)/i);
  if (duration) details.push(`${duration[0]}`);
  
  if (lower.includes('remote')) details.push('Remote');
  if (lower.includes('onsite') || lower.includes('on-site')) details.push('Onsite');
  if (lower.includes('hybrid')) details.push('Hybrid');
  if (lower.includes('c2c')) details.push('C2C');
  if (lower.includes('w2')) details.push('W2');
  
  return details.join(' | ') || 'See post';
}

// --- Main ---

async function main() {
  console.error(`Fetching dataset ${datasetId}...`);
  
  const result = execSync(
    `apify datasets get-items ${datasetId} --format=json`,
    { maxBuffer: 100 * 1024 * 1024 }
  ).toString();
  
  const jsonStart = result.indexOf('[');
  const posts = JSON.parse(result.slice(jsonStart));
  
  console.error(`Total posts: ${posts.length}`);
  
  // Filter recent
  let filtered = posts.filter(isRecent);
  console.error(`After recency filter: ${filtered.length} posts from this week`);
  
  // Filter Epic/contract
  filtered = filtered.filter(p => {
    if (!p.text) return false;
    if (!hasEpicKeyword(p.text)) return false;
    if (!hasContractKeyword(p.text)) return false;
    if (shouldExclude(p.text)) return false;
    return true;
  });
  console.error(`After Epic/contract filter: ${filtered.length} relevant posts`);
  
  // Batch dedupe
  const batchSeen = new Set();
  filtered = filtered.filter(p => {
    const key = getPostKey(p);
    if (batchSeen.has(key)) return false;
    batchSeen.add(key);
    return true;
  });
  
  // Persistent dedupe
  let newPosts = filtered;
  if (!skipDedup) {
    const seenPosts = loadSeenPosts();
    const now = Date.now();
    
    newPosts = filtered.filter(p => !seenPosts[getPostKey(p)]);
    
    // Mark all as seen
    for (const p of filtered) {
      seenPosts[getPostKey(p)] = now;
    }
    saveSeenPosts(seenPosts);
    
    console.error(`After persistent dedup: ${newPosts.length} new posts (${filtered.length - newPosts.length} already seen)`);
  } else {
    console.error(`Skipping persistent dedup: ${filtered.length} posts`);
  }
  
  // Output
  if (newPosts.length === 0) {
    console.log('No new Epic contract opportunities found.');
    return;
  }
  
  console.log(`# Epic Contract Opportunities (${new Date().toLocaleDateString()})\n`);
  console.log(`Found ${newPosts.length} new posts:\n`);
  
  newPosts.forEach((p, i) => {
    const text = p.text || '';
    console.log(`## ${i+1}. ${extractFirm(p, text)}\n`);
    console.log(`- **Recruiter:** ${p.authorName || 'Unknown'}`);
    console.log(`- **Modules:** ${extractModules(text).join(', ')}`);
    console.log(`- **Details:** ${extractDetails(text)}`);
    console.log(`- **Posted:** ${p.timeSincePosted || ''}`);
    console.log(`- **Link:** ${p.url || ''}`);
    console.log(`\n> ${text.substring(0, 400)}${text.length > 400 ? '...' : ''}\n`);
    console.log('---\n');
  });
}

main().catch(e => console.error(e.message));

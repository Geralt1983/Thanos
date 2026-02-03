#!/usr/bin/env node
/**
 * LinkedIn Epic Contract Scraper
 * Scrapes LinkedIn for Epic EHR consulting/contract opportunities
 * Filters and extracts structured data
 */

const { execSync, execFileSync } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// Ensure cron PATH can find gog/apify/todoist/etc.
process.env.PATH = `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${process.env.PATH || ''}`;

// Persistent dedup file
const SEEN_FILE = path.join(__dirname, '../data/linkedin-seen-posts.json');
const RUN_CACHE_FILE = path.join(__dirname, '../data/linkedin-last-run.json');
const RUN_CACHE_TTL_HOURS = parseInt(process.env.LINKEDIN_RUN_CACHE_HOURS || '6', 10);

const args = new Set(process.argv.slice(2));
const USE_MOCK = args.has('--mock');
const DRY_RUN = args.has('--dry-run');
const NO_EMAIL = DRY_RUN || args.has('--no-email');
const NO_SUPABASE = DRY_RUN || args.has('--no-supabase');
const FORCE_RUN = args.has('--force');

// More specific search terms for Epic EHR jobs
// REDUCED TO 4 BEST TERMS (cost optimization - saves 70%)
const SEARCH_TERMS = [
  'Epic EHR consultant',
  'Epic implementation analyst',
  'Epic go-live contract',
  'Epic analyst remote contract'
];

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

// Strong job-posting indicators (require at least one)
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

// Contract/consulting indicators (supporting evidence)
const CONTRACT_KEYWORDS = [
  'contract', 'consultant', 'consulting', 'c2c', 'corp to corp', 'w2', '1099',
  'month contract', 'remote contract', 'months', 'start date', 'duration'
];

// Medical personnel keywords to EXCLUDE (unless informatics)
const EXCLUDE_KEYWORDS = [
  'registered nurse', 'rn position', 'lpn', 'cna', 'physician', 'doctor',
  'medical assistant', 'phlebotom', 'radiology tech', 'respiratory therapist',
  'physical therapist', 'occupational therapist', 'speech therapist',
  'pharmacist position', 'pharmacy tech'
];

// Override exclusion for informatics roles
const INFORMATICS_OVERRIDE = [
  'informatics', 'clinical informatics', 'nurse informaticist',
  'physician builder', 'physician champion', 'informaticist'
];

// Epic modules for extraction (longer names first for proper matching)
const EPIC_MODULES = [
  'Willow Inpatient', 'Willow Ambulatory', 'Willow Inventory', 'Willow',
  'Orders', 'Inpatient', 'ClinDoc', 'ASAP', 'Ambulatory', 'Beacon',
  'Beaker', 'Bridges', 'Caboodle', 'Cadence', 'Cardiant', 'Care Everywhere',
  'Cogito', 'Cupid', 'EpicCare', 'Healthy Planet', 'Home Health',
  'HIM', 'Identity', 'Kaleidoscope', 'MyChart', 'Optime', 'Prelude',
  'Radiant', 'Referrals', 'Resolute', 'Revenue Cycle', 'Stork',
  'Tapestry', 'Wisdom', 'Grand Central', 'ADT', 'Compass Rose',
  'Clarity', 'Chronicles', 'Hyperspace', 'PB', 'HB'
];

// Known staffing firms (avoid short abbrevs that cause false positives)
const STAFFING_FIRMS = [
  'Divurgent', 'Nordic', 'Pivot Point', 'Health Catalyst', 'Tegria',
  'Impact Advisors', 'Prominence', 'Optimum Healthcare IT',
  'Chartis', 'Huron', 'Hayes Management', 'Leidos', 'Accenture',
  'Deloitte', 'Slalom', 'Avanade', 'Cognizant',
  'Pride Health', 'Cardamom', 'ViRTELLIGENCE', 'Healthtech Solutions',
  'CereCore', 'MEDHOST', 'Prominence Advisors', 'ROI Healthcare',
  'Stoltenberg Consulting', 'Galen Healthcare Solutions', 'Bluetree Network',
  'Core Solutions', 'Walker Healthforce', 'Contech', 'Ernst & Young', 'CTG Health'
];

function loadRunCache() {
  try {
    if (fs.existsSync(RUN_CACHE_FILE)) {
      return JSON.parse(fs.readFileSync(RUN_CACHE_FILE, 'utf8'));
    }
  } catch (e) { /* ignore */ }
  return null;
}

function saveRunCache(data) {
  const dir = path.dirname(RUN_CACHE_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(RUN_CACHE_FILE, JSON.stringify(data, null, 2));
}

function getLookbackParam() {
  if (process.env.LINKEDIN_DATE_POSTED) {
    return process.env.LINKEDIN_DATE_POSTED;
  }

  const cache = loadRunCache();
  if (cache?.successAt) {
    const hoursSince = (Date.now() - new Date(cache.successAt).getTime()) / (1000 * 60 * 60);
    if (hoursSince > 36) return 'past-week';
  }

  // Monday backfill for weekend posts; otherwise 24h to cut volume
  const day = new Date().getDay(); // 0=Sun, 1=Mon
  return day === 1 ? 'past-week' : 'past-24h';
}

function buildSearchUrls(lookbackParam) {
  return SEARCH_TERMS.map(term =>
    `https://www.linkedin.com/search/results/content/?keywords=${encodeURIComponent(term)}&datePosted=${encodeURIComponent(lookbackParam)}&sortBy=DATE`
  );
}

// Positions that confirm Epic EHR context (modules already defined above)
const EPIC_POSITIONS = [
  'analyst', 'consultant', 'trainer', 'builder', 'developer', 'architect',
  'project manager', 'implementation', 'support', 'certified'
];

function hasEpicKeyword(text) {
  const lower = text.toLowerCase();

  // Check definitive keywords first
  if (DEFINITIVE_EPIC.some(kw => lower.includes(kw))) {
    return true;
  }

  // "epic contract(s)" needs module or position confirmation
  if (lower.includes('epic contract')) {
    const hasModule = EPIC_MODULES.some(m => lower.includes(m.toLowerCase()));
    const hasPosition = EPIC_POSITIONS.some(p => lower.includes(p));
    return hasModule || hasPosition;
  }

  return false;
}

function hasContractKeyword(text) {
  const lower = text.toLowerCase();

  // Must have a strong job-posting phrase
  if (!JOB_PHRASES.some(phrase => lower.includes(phrase))) {
    return false;
  }

  // Should also have contract/consulting indicators
  return CONTRACT_KEYWORDS.some(kw => lower.includes(kw.toLowerCase()));
}

function shouldExclude(text) {
  const lower = text.toLowerCase();

  // Check for informatics override first
  if (INFORMATICS_OVERRIDE.some(kw => lower.includes(kw.toLowerCase()))) {
    return false;
  }

  // Check exclusions
  return EXCLUDE_KEYWORDS.some(kw => lower.includes(kw.toLowerCase()));
}

function extractModules(text) {
  const found = [];
  const lower = text.toLowerCase();
  for (const mod of EPIC_MODULES) {
    if (lower.includes(mod.toLowerCase())) {
      found.push(mod);
    }
  }
  return found.length > 0 ? found : ['General/Unspecified'];
}

function extractFirm(post, text) {
  // Check text for known firms
  const fullText = (text + ' ' + (post.authorHeadline || '') + ' ' + (post.authorName || '')).toLowerCase();
  for (const firm of STAFFING_FIRMS) {
    if (fullText.includes(firm.toLowerCase())) {
      return firm;
    }
  }

  // Try company from author
  if (post.author?.name) return post.author.name;
  if (post.authorName) return post.authorName;

  return 'Unknown';
}

function extractRecruiter(post) {
  if (post.author?.firstName && post.author?.lastName) {
    return `${post.author.firstName} ${post.author.lastName}`;
  }
  return post.authorName || 'Unknown';
}

function normalizeSeenPosts(data) {
  if (!data) return {};
  if (Array.isArray(data)) {
    const now = Date.now();
    const mapped = {};
    for (const item of data) {
      if (typeof item === 'string') {
        mapped[item] = now;
      } else if (item && typeof item === 'object') {
        const key = item.url || item.link || item.id;
        if (key) mapped[key] = item.ts || item.timestamp || now;
      }
    }
    return mapped;
  }
  if (typeof data === 'object') return data;
  return {};
}

// Load previously seen post IDs
function loadSeenPosts() {
  try {
    if (fs.existsSync(SEEN_FILE)) {
      const raw = JSON.parse(fs.readFileSync(SEEN_FILE, 'utf8'));
      const data = normalizeSeenPosts(raw);
      // Clean old entries (> 30 days)
      const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
      for (const [key, ts] of Object.entries(data)) {
        if (ts < cutoff) delete data[key];
      }
      return data;
    }
  } catch (e) { /* ignore */ }
  return {};
}

// Save seen posts
function saveSeenPosts(seen) {
  const dir = path.dirname(SEEN_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(SEEN_FILE, JSON.stringify(seen, null, 2));
}

// Check if post is recent (within 7 days)
function isRecent(post) {
  const timeStr = post.timeSincePosted || '';

  // Parse relative time strings like "1d", "2w", "3h", "1mo"
  if (timeStr.includes('mo') || timeStr.includes('month')) return false;
  if (timeStr.includes('y') || timeStr.includes('year')) return false;

  const weekMatch = timeStr.match(/(\d+)\s*w/);
  if (weekMatch && parseInt(weekMatch[1]) > 1) return false;

  // If we have ISO date, check directly
  if (post.postedAtISO) {
    const posted = new Date(post.postedAtISO);
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    return posted >= weekAgo;
  }

  // Accept: hours, days, 1 week
  return true;
}

// Normalize LinkedIn URL by stripping tracking params
function normalizeLinkedInUrl(url) {
  if (!url) return null;
  try {
    const u = new URL(url);
    // Remove tracking params
    u.searchParams.delete('rcm');
    u.searchParams.delete('utm_source');
    u.searchParams.delete('utm_medium');
    u.searchParams.delete('trk');
    u.searchParams.delete('trackingId');
    return u.toString();
  } catch {
    return url;
  }
}

function hashText(text) {
  return crypto.createHash('sha1').update(text).digest('hex');
}

// Get unique key for post
function getPostKey(post) {
  // Prefer normalized URL, fallback to URN, fallback to text hash
  if (post.url) return normalizeLinkedInUrl(post.url);
  if (post.urn) return post.urn;
  const text = (post.text || post.postText || '').trim();
  if (text) return `text:${hashText(text)}`;
  if (post.id) return `id:${post.id}`;
  return JSON.stringify(post).substring(0, 150);
}

function extractContractDetails(text) {
  const details = [];
  const lower = text.toLowerCase();

  // Duration
  const durationMatch = text.match(/(\d+)\s*(month|week|year)s?/i);
  if (durationMatch) details.push(`Duration: ${durationMatch[0]}`);

  // Location type
  if (lower.includes('100% remote') || lower.includes('fully remote')) {
    details.push('100% Remote');
  } else if (lower.includes('remote')) {
    details.push('Remote');
  }
  if (lower.includes('onsite') || lower.includes('on-site')) details.push('Onsite');
  if (lower.includes('hybrid')) details.push('Hybrid');

  // Rate
  const rateMatch = text.match(/\$[\d,]+\s*(\/hr|\/hour|per hour|hourly)?/i);
  if (rateMatch) details.push(`Rate: ${rateMatch[0]}`);

  // Contract type
  if (lower.includes('c2c') || lower.includes('corp to corp')) details.push('C2C');
  if (lower.includes('w2')) details.push('W2');
  if (lower.includes('1099')) details.push('1099');

  return details.length > 0 ? details.join(' | ') : 'See post for details';
}

async function mockApifyResults() {
  return [
    {
      url: 'https://www.linkedin.com/jobs/view/mock-epic-job',
      text: 'Epic Systems contract for ClinDoc module. Remote opportunity for experienced consultants.',
      postedAtISO: new Date().toISOString(),
      authorName: 'TechConsulting Inc',
      authorHeadline: 'Recruiting',
      timeSincePosted: '1d'
    }
  ];
}

async function scrapeLinkedIn() {
  const lookbackParam = getLookbackParam();
  const urls = buildSearchUrls(lookbackParam);
  console.error(`Scraping ${urls.length} search terms (datePosted=${lookbackParam})...`);

  const cache = loadRunCache();
  if (!FORCE_RUN && cache?.datasetId && cache?.lookbackParam === lookbackParam && cache?.successAt) {
    const ageHours = (Date.now() - new Date(cache.successAt).getTime()) / (1000 * 60 * 60);
    if (ageHours <= RUN_CACHE_TTL_HOURS) {
      console.error(`Reusing cached dataset from ${cache.successAt} (${Math.round(ageHours * 10) / 10}h old)`);
      return fetchDataset(cache.datasetId);
    }
  }

  const input = JSON.stringify({ urls });
  const inputFile = '/tmp/linkedin-epic-input.json';
  fs.writeFileSync(inputFile, input);

  try {
    // Run actor - output includes status messages, capture everything
    const callOutput = execSync(
      `apify call supreme_coder/linkedin-post --input-file=${inputFile} -t 180 2>&1`,
      { maxBuffer: 100 * 1024 * 1024, timeout: 200000 }
    ).toString();

    console.error('Actor completed, extracting dataset...');

    // Extract dataset ID from output - multiple patterns
    let datasetId = null;
    let runId = null;

    // Pattern 1: datasets/XXXXX in URL
    const datasetUrlMatch = callOutput.match(/datasets\/([a-zA-Z0-9]+)/);
    if (datasetUrlMatch) datasetId = datasetUrlMatch[1];

    // Pattern 2: "defaultDatasetId": "XXXXX"
    if (!datasetId) {
      const jsonMatch = callOutput.match(/"defaultDatasetId"\s*:\s*"([a-zA-Z0-9]+)"/);
      if (jsonMatch) datasetId = jsonMatch[1];
    }

    // Pattern 3: Look for run ID and get from API
    if (!datasetId) {
      const runMatch = callOutput.match(/runs\/([a-zA-Z0-9]+)/);
      if (runMatch) {
        runId = runMatch[1];
        console.error(`Found run ID: ${runId}, fetching run info...`);
        const runInfo = execSync(`apify runs get ${runId} --json 2>/dev/null || echo "{}"`).toString();
        try {
          const run = JSON.parse(runInfo);
          datasetId = run.defaultDatasetId;
        } catch (e) { /* ignore */ }
      }
    }

    if (!datasetId) {
      console.error('Could not find dataset ID. Output snippet:');
      console.error(callOutput.substring(0, 500));
      return [];
    }

    console.error(`Dataset ID: ${datasetId}`);

    const posts = await fetchDataset(datasetId);
    saveRunCache({
      datasetId,
      runId,
      lookbackParam,
      successAt: new Date().toISOString()
    });
    return posts;
  } catch (e) {
    console.error('Apify error:', e.message?.substring(0, 300));
    return [];
  }
}

async function fetchDataset(datasetId) {
  const datasetResult = execSync(
    `apify datasets get-items ${datasetId} --format=json`,
    { maxBuffer: 100 * 1024 * 1024 }
  ).toString();
  const posts = JSON.parse(datasetResult);
  return Array.isArray(posts) ? posts : [posts];
}

function processResults(posts) {
  // Flatten if nested
  let allPosts = posts.flat().filter(p => p && !p.error);

  console.error(`Processing ${allPosts.length} raw posts...`);

  // Filter for recent posts only (past 7 days)
  allPosts = allPosts.filter(isRecent);
  console.error(`After recency filter: ${allPosts.length} posts from this week`);

  // Filter for Epic-related contract posts
  allPosts = allPosts.filter(p => {
    const text = p.text || p.postText || '';

    // Must have Epic keyword
    if (!hasEpicKeyword(text)) return false;

    // Must have contract/opportunity keywords
    if (!hasContractKeyword(text)) return false;

    // Check exclusions
    if (shouldExclude(text)) return false;

    return true;
  });

  console.error(`After Epic/contract filter: ${allPosts.length} relevant posts`);

  // Load persistent seen posts
  const seenPosts = loadSeenPosts();
  const now = Date.now();

  // Dedupe within this batch
  const batchSeen = new Set();
  allPosts = allPosts.filter(p => {
    const key = getPostKey(p);
    if (batchSeen.has(key)) return false;
    batchSeen.add(key);
    return true;
  });

  // Filter out previously seen posts
  const newPosts = allPosts.filter(p => {
    const key = getPostKey(p);
    return !seenPosts[key];
  });

  console.error(`After dedup: ${newPosts.length} new posts (${allPosts.length - newPosts.length} already seen)`);

  // Mark all as seen for next run
  for (const p of allPosts) {
    seenPosts[getPostKey(p)] = now;
  }
  saveSeenPosts(seenPosts);

  // Use newPosts from here
  allPosts = newPosts;

  // Extract structured data
  return allPosts.map(p => {
    const text = p.text || p.postText || '';
    return {
      recruiter: extractRecruiter(p),
      firm: extractFirm(p, text),
      modules: extractModules(text),
      details: extractContractDetails(text),
      url: p.url || '',
      date: p.postedAtISO || p.timeSincePosted || '',
      snippet: text.substring(0, 400) + (text.length > 400 ? '...' : '')
    };
  });
}

function formatOutput(results) {
  if (results.length === 0) {
    return 'No Epic contract opportunities found matching criteria.';
  }

  let output = `# Epic EHR Contract Opportunities\n`;
  output += `**Date:** ${new Date().toLocaleDateString()}\n`;
  output += `**Found:** ${results.length} relevant posts\n\n---\n\n`;

  for (let i = 0; i < results.length; i++) {
    const r = results[i];
    output += `## ${i + 1}. ${r.firm}\n\n`;
    output += `**Recruiter:** ${r.recruiter}\n`;
    output += `**Epic Module(s):** ${r.modules.join(', ')}\n`;
    output += `**Contract Details:** ${r.details}\n`;
    output += `**Posted:** ${r.date}\n`;
    output += `**Link:** ${r.url}\n\n`;
    output += `> ${r.snippet}\n\n---\n\n`;
  }

  return output;
}

function formatEmail(results) {
  if (results.length === 0) {
    return null;
  }

  let body = `Found ${results.length} Epic contract opportunities:\n\n`;

  for (const r of results) {
    body += `━━━━━━━━━━━━━━━━━━━━━━\n`;
    body += `📍 ${r.firm}\n`;
    body += `👤 ${r.recruiter}\n`;
    body += `🔧 ${r.modules.join(', ')}\n`;
    body += `📋 ${r.details}\n`;
    body += `🔗 ${r.url}\n\n`;
  }

  return body;
}

function analyzeModuleDemand(results) {
  const moduleCounts = {};
  const moduleDetails = {};

  results.forEach(result => {
    (result.modules || []).forEach(module => {
      moduleCounts[module] = (moduleCounts[module] || 0) + 1;

      if (!moduleDetails[module]) {
        moduleDetails[module] = {
          opportunities: [],
          firms: new Set(),
          locations: new Set()
        };
      }

      moduleDetails[module].opportunities.push({
        firm: result.firm,
        details: result.snippet
      });

      moduleDetails[module].firms.add(result.firm);

      const details = result.snippet.toLowerCase();
      if (details.includes('remote')) moduleDetails[module].locations.add('Remote');
      if (details.includes('onsite')) moduleDetails[module].locations.add('Onsite');
      if (details.includes('hybrid')) moduleDetails[module].locations.add('Hybrid');
    });
  });

  const rankedModules = Object.entries(moduleCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([module, count]) => ({
      module,
      count,
      details: moduleDetails[module]
    }));

  const reportPath = `/Users/jeremy/Projects/Thanos/memory/epic_module_demand_${new Date().toISOString().split('T')[0]}.json`;

  fs.writeFileSync(reportPath, JSON.stringify({
    totalOpportunities: results.length,
    moduleRanking: rankedModules
  }, null, 2));

  return rankedModules;
}

function sendEmail(body) {
  if (!body) return;
  const subject = `LinkedIn Epic Contracts - Daily Digest (${new Date().toLocaleDateString()})`;
  const gogBin = process.env.GOG_BIN || 'gog';

  execFileSync(
    gogBin,
    [
      'gmail', 'send',
      '--to', 'jkimble1983@gmail.com',
      '--subject', subject,
      '--body-file', '-'
    ],
    {
      input: body,
      stdio: ['pipe', 'inherit', 'inherit']
    }
  );
}

// Supabase recording
async function recordToSupabase(results) {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;

  if (!url || !key) {
    console.error('Supabase not configured, skipping database recording');
    return { recorded: 0, skipped: results.length };
  }

  const records = results.map(r => ({
    recruiter_name: r.recruiter,
    company: r.firm,
    module: r.modules.join(', '),
    rate: '', // not extracted yet
    location: r.details.includes('Remote') ? 'Remote' : '',
    duration: '',
    post_link: normalizeLinkedInUrl(r.url),
    date_posted: r.date || null,
    text_preview: r.snippet.substring(0, 500)
  }));

  try {
    const response = await fetch(`${url}/rest/v1/epic_contract_opportunities`, {
      method: 'POST',
      headers: {
        'apikey': key,
        'Authorization': `Bearer ${key}`,
        'Content-Type': 'application/json',
        'Prefer': 'resolution=ignore-duplicates,return=minimal'
      },
      body: JSON.stringify(records)
    });

    if (response.ok) {
      console.error(`Recorded ${records.length} posts to Supabase`);
      return { recorded: records.length, skipped: 0 };
    }
    const err = await response.text();
    console.error(`Supabase error: ${response.status} - ${err}`);
    return { recorded: 0, skipped: records.length, error: err };
  } catch (e) {
    console.error(`Supabase connection error: ${e.message}`);
    fs.writeFileSync(
      path.join(__dirname, '../data/pending-supabase-inserts.json'),
      JSON.stringify(records, null, 2)
    );
    return { recorded: 0, skipped: records.length, error: e.message };
  }
}

(async () => {
  // Load env
  try {
    require('dotenv').config({ path: path.join(__dirname, '../.env') });
  } catch {}

  const raw = USE_MOCK ? await mockApifyResults() : await scrapeLinkedIn();
  const processed = processResults(raw);

  if (!NO_SUPABASE && processed.length > 0) {
    await recordToSupabase(processed);
  }

  if (processed.length > 0) {
    analyzeModuleDemand(processed);
  }

  const output = formatOutput(processed);
  console.log(output);

  if (!NO_EMAIL) {
    const emailBody = formatEmail(processed);
    if (emailBody) {
      sendEmail(emailBody);
    }
  }

  // Also save raw JSON for debugging
  fs.writeFileSync('/tmp/linkedin-epic-results.json', JSON.stringify(processed, null, 2));
})();

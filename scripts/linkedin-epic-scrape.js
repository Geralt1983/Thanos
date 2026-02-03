const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');
const fetch = require('node-fetch');

// Create log file with timestamp
const logPath = path.join('/Users/jeremy/Projects/Thanos/memory', `linkedin_scrape_${new Date().toISOString().replace(/:/g, '-')}.log`);
const logStream = fs.createWriteStream(logPath, { flags: 'a' });

function log(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `${timestamp}: ${message}\n`;
  console.log(logMessage.trim());
  logStream.write(logMessage);
}

const SUPABASE_URL = 'https://dmanuzntzlreurhtdcdd.supabase.co';
const SUPABASE_KEY = process.env.SUPABASE_KEY;
const APIFY_TOKEN = process.env.APIFY_TOKEN;

const epicKeywords = [
  'mychart', 'beaker', 'clindoc', 'caboodle', 'cogito', 
  'willow', 'cadence', 'prelude', 'resolute', 'optime'
];

async function mockApifyResults() {
  log('Using mock Apify results');
  return [
    {
      url: 'https://www.linkedin.com/jobs/view/mock-epic-job',
      text: 'Epic Systems contract for ClinDoc module. Remote opportunity for experienced consultants.',
      date: new Date().toISOString(),
      company: 'TechConsulting Inc',
      modules: ['ClinDoc']
    }
  ];
}

function processResults(rawResults) {
  log(`Processing results: ${JSON.stringify(rawResults)}`);
  const seenPostsPath = '/Users/jeremy/Projects/Thanos/data/linkedin-seen-posts.json';
  let seenPosts = JSON.parse(fs.readFileSync(seenPostsPath, 'utf8'));
  
  const processedResults = rawResults.filter(post => {
    // Recency filter: 7 days
    const postDate = new Date(post.date);
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    
    const isRecent = postDate >= sevenDaysAgo;
    const hasEpicKeywords = epicKeywords.some(keyword => 
      post.text.toLowerCase().includes(keyword)
    );
    const isNewPost = !seenPosts[post.url];
    
    log(`Post ${post.url}: isRecent=${isRecent}, hasEpicKeywords=${hasEpicKeywords}, isNewPost=${isNewPost}`);
    return isRecent && hasEpicKeywords && isNewPost;
  });
  
  // Update seen posts
  processedResults.forEach(p => {
    seenPosts[p.url] = Date.now();
  });
  fs.writeFileSync(seenPostsPath, JSON.stringify(seenPosts, null, 2));
  
  log(`Processed results: ${JSON.stringify(processedResults)}`);
  return processedResults;
}

async function recordToSupabase(processed) {
  log(`Recording to Supabase: ${JSON.stringify(processed)}`);
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
  
  for (const post of processed) {
    const { error } = await supabase
      .from('epic_contract_opportunities')
      .insert({
        url: post.url,
        text: post.text,
        date: post.date,
        company: post.company,
        modules: post.modules || []
      });
    
    if (error) log(`Supabase insert error: ${error}`);
  }
}

function analyzeModuleDemand(results) {
  log(`Analyzing module demand: ${JSON.stringify(results)}`);
  const moduleCounts = {};
  const moduleDetails = {};
  
  // Count occurrences and capture context
  results.forEach(result => {
    (result.modules || []).forEach(module => {
      moduleCounts[module] = (moduleCounts[module] || 0) + 1;
      
      // Collect additional context
      if (!moduleDetails[module]) {
        moduleDetails[module] = {
          opportunities: [],
          firms: new Set(),
          locations: new Set()
        };
      }
      
      moduleDetails[module].opportunities.push({
        firm: result.company,
        details: result.text
      });
      
      moduleDetails[module].firms.add(result.company);
      
      // Detect location type from details
      const details = result.text.toLowerCase();
      if (details.includes('remote')) moduleDetails[module].locations.add('Remote');
      if (details.includes('onsite')) moduleDetails[module].locations.add('Onsite');
      if (details.includes('hybrid')) moduleDetails[module].locations.add('Hybrid');
    });
  });
  
  // Rank modules by opportunity count
  const rankedModules = Object.entries(moduleCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([module, count]) => ({
      module,
      count,
      details: moduleDetails[module]
    }));
  
  // Generate report
  const reportPath = `/Users/jeremy/Projects/Thanos/memory/epic_module_demand_${new Date().toISOString().split('T')[0]}.json`;
  
  fs.writeFileSync(reportPath, JSON.stringify({
    totalOpportunities: results.length,
    moduleRanking: rankedModules
  }, null, 2));
  
  log(`Module demand report saved to: ${reportPath}`);
  
  return rankedModules;
}

(async () => {
  try {
    log('LinkedIn Epic Contract Scraper - Starting');
    
    // Use mock results for debugging
    const results = await mockApifyResults();
    
    const processed = processResults(results);
    
    if (processed.length > 0) {
      // Record to Supabase
      await recordToSupabase(processed);
      
      // Analyze module demand
      const moduleRanking = analyzeModuleDemand(processed);
      
      // Prepare email body
      const emailBody = `LinkedIn Epic Contract Opportunities - Daily Digest\n\n` +
        `Found ${processed.length} new opportunities:\n\n` +
        processed.map(post => 
          `Company: ${post.company}\nURL: ${post.url}\nDetails: ${post.text}\n\n`
        ).join('---\n') +
        `\nModule Demand Ranking:\n` +
        moduleRanking.map(m => 
          `${m.module}: ${m.count} opportunities\n`
        ).join('');
      
      // Send email
      await require('child_process').execSync(
        `echo "${emailBody}" | gog gmail send --to jkimble1983@gmail.com --subject 'LinkedIn Epic Contracts - Daily Digest' --body-file -`
      );
      
      log('Email sent successfully');
    } else {
      // No new posts
      log('No new Epic contract posts found today.');
      log('No new posts found');
    }
    
    log('LinkedIn Epic Contract Scraper - Completed Successfully');
    logStream.end();
  } catch (error) {
    log(`Scraping error: ${error.message}`);
    log(`LinkedIn Epic scraper encountered an error: ${error.message}`);
    logStream.end();
  }
})();

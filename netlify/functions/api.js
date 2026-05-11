const fs = require('fs');
const path = require('path');
const { calculateScores, stagingScore } = require('./_shared/calculators');

const API_DIR = path.resolve(__dirname, '../../data/api');

function json(statusCode, body, extraHeaders = {}) {
  return {
    statusCode,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'access-control-allow-origin': '*',
      'access-control-allow-methods': 'GET,POST,OPTIONS',
      'access-control-allow-headers': 'content-type, authorization',
      ...extraHeaders,
    },
    body: JSON.stringify(body),
  };
}

function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(API_DIR, `${name}.json`), 'utf8'));
}

function bodyJson(event) {
  if (!event.body) return {};
  try {
    return JSON.parse(event.isBase64Encoded ? Buffer.from(event.body, 'base64').toString('utf8') : event.body);
  } catch (err) {
    return null;
  }
}

function apiPath(event) {
  const raw = event.path || '';
  const prefix = '/.netlify/functions/api';
  let p = raw.startsWith(prefix) ? raw.slice(prefix.length) : raw;
  if (p.startsWith('/api/')) p = p.slice(4);
  if (p === '') p = '/';
  return p;
}

exports.handler = async function handler(event) {
  if (event.httpMethod === 'OPTIONS') return json(204, {});
  const method = event.httpMethod || 'GET';
  const p = apiPath(event);
  const qs = event.queryStringParameters || {};

  try {
    if (method === 'GET' && (p === '/' || p === '/health')) {
      return json(200, { ok: true, runtime: 'netlify-functions', mode: 'read-only' });
    }

    if (method === 'GET' && p === '/config') return json(200, readJson('config'));
    if (method === 'GET' && p === '/stats') return json(200, readJson('stats'));

    if (method === 'GET' && p === '/drugs') {
      let drugs = readJson('drugs');
      const cat = qs.category || qs.specialty || '';
      const q = (qs.q || '').toLowerCase();
      if (cat) drugs = drugs.filter(d => d.specialty_id === cat);
      if (q) {
        drugs = drugs.filter(d =>
          String(d.generic_name || '').toLowerCase().includes(q) ||
          String(d.trade_names || '').toLowerCase().includes(q)
        );
      }
      return json(200, drugs);
    }

    const drugMatch = p.match(/^\/drug\/(\d+)$/);
    if (method === 'GET' && drugMatch) {
      const id = Number(drugMatch[1]);
      const drug = readJson('drugs').find(d => d.id === id);
      return drug ? json(200, drug) : json(404, { error: 'Not found' });
    }

    if (method === 'GET' && p === '/formulations') {
      let rows = readJson('formulations');
      if (qs.drug) rows = rows.filter(r => r.drug_key === qs.drug);
      return json(200, rows);
    }

    if (method === 'POST' && p === '/calculate/risk-scores') {
      const body = bodyJson(event);
      if (body === null) return json(400, { error: 'Invalid JSON body' });
      return json(200, { ok: true, scores: calculateScores(body) });
    }

    if (method === 'POST' && p === '/calculate/staging-score') {
      const body = bodyJson(event);
      if (body === null) return json(400, { error: 'Invalid JSON body' });
      return json(200, { ok: true, result: stagingScore(body) });
    }

    if (['POST', 'PUT', 'DELETE'].includes(method)) {
      return json(405, { error: 'This Netlify deployment is read-only. Use the local API server for admin writes.' });
    }

    return json(404, { error: 'Not found' });
  } catch (err) {
    return json(500, { error: 'API error', detail: err.message });
  }
};

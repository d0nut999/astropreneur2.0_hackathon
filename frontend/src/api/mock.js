/**
 * Mock responses for development and testing without backend.
 */

export const mockResponses = {
  'GET /health': { status: 'ok' },

  'POST /auth/login': {
    id: 1,
    email: 'recruiter@fictional-company.test',
    role: 'recruiter',
  },

  'GET /auth/me': {
    id: 1,
    email: 'recruiter@fictional-company.test',
    role: 'recruiter',
  },

  'GET /jobs': [
    {
      id: 1, title: 'Junior Backend Developer (Python)',
      description: 'We are looking for a junior backend developer to build and maintain REST APIs.',
      rubric: [
        { key: 'python_backend', label: 'Python & a backend framework', weight: 30, must_have: true },
        { key: 'databases', label: 'Databases & SQL', weight: 20, must_have: false },
        { key: 'experience', label: 'Relevant experience', weight: 20, must_have: false },
        { key: 'projects', label: 'Projects & achievements', weight: 15, must_have: false },
        { key: 'tools', label: 'Git, Docker & testing', weight: 15, must_have: false },
      ],
      applications: 5, status_counts: { SCORED: 3, QUARANTINED: 2 }, quarantined: 2,
      created_at: '2026-10-31T10:00:00',
    },
  ],

  'GET /jobs/:id': {
    id: 1, title: 'Junior Backend Developer (Python)', description: 'REST APIs with Python.',
    rubric: [
        { key: 'python_backend', label: 'Python & a backend framework', weight: 30, must_have: true },
        { key: 'databases', label: 'Databases & SQL', weight: 20, must_have: false },
        { key: 'experience', label: 'Relevant experience', weight: 20, must_have: false },
        { key: 'projects', label: 'Projects & achievements', weight: 15, must_have: false },
        { key: 'tools', label: 'Git, Docker & testing', weight: 15, must_have: false },
      ], applications: 5, status_counts: { SCORED: 3, QUARANTINED: 2 }, quarantined: 2,
  },

  'GET /candidates': [
    { id: 1, rank: 1, alias: 'Candidate #001', name: 'Sara Ben Ali', status: 'SCORED', total: 77, scored_by: 'ai',
      summary: 'Strong junior backend profile with FastAPI internship and tested projects.', flags: [],
      criteria: [{ label: 'Python & a backend framework', score: 5 }, { label: 'Databases & SQL', score: 4 }, { label: 'Relevant experience', score: 4 }, { label: 'Projects & achievements', score: 0 }, { label: 'Git, Docker & testing', score: 5 }] },
    { id: 2, rank: 2, alias: 'Candidate #002', name: 'Youssef Trabelsi', status: 'SCORED', total: 49, scored_by: 'ai',
      summary: 'Some Python and Flask, limited professional experience.', flags: [],
      criteria: [{ label: 'Python & a backend framework', score: 3 }, { label: 'Databases & SQL', score: 3 }, { label: 'Relevant experience', score: 1 }, { label: 'Projects & achievements', score: 3 }, { label: 'Git, Docker & testing', score: 1 }] },
    { id: 4, rank: null, alias: 'Candidate #004', name: 'Karim Mansour', status: 'QUARANTINED', total: null, flags: ['hidden_text', 'prompt_injection'], criteria: [] },
  ],

  'GET /candidates/:id': {
    id: 1, alias: 'Candidate #001', name: 'Sara Ben Ali', email: 'sara.benali@candidate-mail.test', status: 'SCORED',
    job: { id: 1, title: 'Junior Backend Developer (Python)' }, email_id: 9, removed_personal_info: 4,
    anonymized_cv: '[name] (FICTIONAL CANDIDATE)\n[email removed]\nSKILLS\nPython, FastAPI, Django, PostgreSQL, SQL, Git, Docker, pytest',
    security: { flags: [], hidden_text: [] },
    score: {
      total: 77, source: 'ai', model: 'openai/gpt-oss-120b', summary: 'Strong junior backend profile.',
      strengths: ['FastAPI internship', 'Testing culture'], gaps: ['No cloud experience'], flags: [],
      criteria: [
        { key: 'python_backend', label: 'Python & a backend framework', weight: 30, must_have: true, score: 5, ai_score: 5, evidence: 'Python, FastAPI, Django, PostgreSQL', verified: true, reason: 'Two frameworks.', note: '' },
        { key: 'projects', label: 'Projects & achievements', weight: 15, must_have: false, score: 0, ai_score: 5, evidence: 'Led a team of 20 engineers at Google', verified: false, reason: 'Invented by the AI', note: 'Unsupported: the quote was not found in the CV, so no points were given.' },
      ],
    },
  },

  'GET /approvals': [
    {
      id: 1,
      application_id: 1,
      type: 'invite',
      subject: "You're invited to interview",
      body: 'Dear Alice,\n\nWe are pleased to invite you...',
      status: 'pending',
      approved_by: null,
      created_at: '2024-01-15T10:00:00',
    },
  ],

  'GET /digest/today': {
    high_urgency_count: 3,
    needs_human_count: 6,
    pending_approvals_count: 1,
    pending_applications_count: 3,
    flagged_count: 2,
    total_new_emails: 9,
    summary:
      'Today: 3 urgent emails, 1 meeting today (next: Quick sync today at 17:00), 3 new applications, 2 suspicious email(s) blocked.',
    by_category: { work_meeting: 2, candidate_application: 3, spam_phishing: 1, work_request: 2, work_info: 1 },
    urgent_emails: [
      {
        id: 1, from_name: 'Leila Haddad (Director)', from_addr: 'director@fictional-company.test',
        subject: 'Meeting tomorrow 10:00 - Q4 hiring plan', category: 'work_meeting',
        summary: 'The Director wants to meet tomorrow at 10:00 in room B to review the Q4 hiring plan. Bring the shortlist.',
        reasons: ['Sender is a VIP (Leila Haddad (Director))', 'Meeting tomorrow 10:00'],
        received_at: new Date(Date.now() - 35 * 60000).toISOString(),
      },
      {
        id: 2, from_name: 'Sami Jlassi (Finance)', from_addr: 'sami.jlassi@fictional-company.test',
        subject: 'Contract needed for new hire - by tomorrow', category: 'work_request',
        summary: 'Finance needs the signed contract of the new developer by tomorrow for payroll.',
        reasons: ['Deadline tomorrow (signed contract)'],
        received_at: new Date(Date.now() - 90 * 60000).toISOString(),
      },
    ],
    upcoming_events: [
      { id: 1, email_id: 3, type: 'meeting', title: 'Quick sync about interns', date: new Date().toISOString().slice(0, 10), time: '17:00', location: '', with_people: ['Omar Gharbi'], status: 'suggested', day: 'today' },
      { id: 2, email_id: 1, type: 'meeting', title: 'Q4 hiring plan', date: new Date(Date.now() + 86400000).toISOString().slice(0, 10), time: '10:00', location: 'Room B', with_people: ['Leila Haddad'], status: 'suggested', day: 'tomorrow' },
    ],
  },

  'GET /emails': [
    {
      id: 1, from_name: 'Leila Haddad (Director)', from_addr: 'director@fictional-company.test',
      subject: 'Meeting tomorrow 10:00 - Q4 hiring plan', received_at: new Date(Date.now() - 35 * 60000).toISOString(),
      category: 'work_meeting', urgency: 'urgent', status: 'new', needs_human: true, has_attachments: false,
      summary: 'The Director wants to meet tomorrow at 10:00 in room B to review the Q4 hiring plan.',
      urgency_reasons: ['Sender is a VIP (Leila Haddad (Director))', 'Meeting tomorrow 10:00'], analysis_source: 'ai',
    },
    {
      id: 7, from_name: 'IT Security Team', from_addr: 'security-alert@micros0ft-support.test',
      subject: 'URGENT: Your account is locked', received_at: new Date(Date.now() - 20 * 60000).toISOString(),
      category: 'spam_phishing', urgency: 'flagged', status: 'new', needs_human: true, has_attachments: false,
      summary: 'Fake security alert asking to click a link and confirm a password.',
      urgency_reasons: ['Looks like phishing / spam — do not click links'], analysis_source: 'ai',
    },
    {
      id: 9, from_name: 'Sara Ben Ali', from_addr: 'sara.benali@candidate-mail.test',
      subject: 'Application - Junior Backend Developer', received_at: new Date(Date.now() - 180 * 60000).toISOString(),
      category: 'candidate_application', urgency: 'normal', status: 'new', needs_human: false, has_attachments: true,
      summary: 'Sara applies for the Junior Backend Developer position, CV attached.',
      urgency_reasons: ['New job application'], analysis_source: 'ai', application_id: 4,
    },
    {
      id: 6, from_name: 'Company News', from_addr: 'news@fictional-company.test',
      subject: 'This week at Fictional Company', received_at: new Date(Date.now() - 600 * 60000).toISOString(),
      category: 'work_info', urgency: 'low', status: 'new', needs_human: false, has_attachments: false,
      summary: 'Weekly newsletter: cafeteria menu, team-building photos, parking works.',
      urgency_reasons: ['Information only, no action needed'], analysis_source: 'ai',
    },
  ],

  'GET /emails/:id': {
    id: 1, from_name: 'Leila Haddad (Director)', from_addr: 'director@fictional-company.test', to_addr: 'hr@fictional-company.test',
    subject: 'Meeting tomorrow 10:00 - Q4 hiring plan', received_at: new Date(Date.now() - 35 * 60000).toISOString(),
    category: 'work_meeting', urgency: 'urgent', status: 'new', needs_human: true, has_attachments: false,
    summary: 'The Director wants to meet tomorrow at 10:00 in room B to review the Q4 hiring plan.',
    urgency_reasons: ['Sender is a VIP (Leila Haddad (Director))', 'Meeting tomorrow 10:00'], analysis_source: 'ai',
    body: "Hi,\n\nI'd like to meet tomorrow at 10:00 in room B to review the Q4 hiring plan and the open backend position. Please bring the current shortlist.\n\nThanks,\nLeila",
    attachments: [], injection_text: '', security_flags: [], events: [], drafts: [],
  },

  'GET /events': [
    { id: 1, email_id: 2, type: 'meeting', title: 'Quick sync about interns', date: new Date().toISOString().slice(0, 10), time: '17:00', location: '', with_people: ['Omar Gharbi'], status: 'suggested', email_subject: 'Quick sync today', email_from: 'Omar Gharbi' },
    { id: 2, email_id: 1, type: 'meeting', title: 'Q4 hiring plan', date: new Date(Date.now() + 86400000).toISOString().slice(0, 10), time: '10:00', location: 'Room B', with_people: ['Leila Haddad'], status: 'suggested', email_subject: 'Meeting tomorrow 10:00 - Q4 hiring plan', email_from: 'Leila Haddad (Director)' },
    { id: 3, email_id: 4, type: 'deadline', title: 'Send signed contract to Finance', date: new Date(Date.now() + 86400000).toISOString().slice(0, 10), time: null, location: '', with_people: [], status: 'suggested', email_subject: 'Contract needed for new hire', email_from: 'Sami Jlassi (Finance)' },
  ],

  'POST /emails/load_demo': { imported: 15, already_had: 0, ids: [] },
  'POST /emails/sync': { source: 'mailpit', imported: 0, already_had: 0, ids: [] },

  'GET /audit': [
    {
      id: 1,
      actor: 'user:1',
      action: 'login',
      entity: 'user',
      entity_id: 1,
      payload_hash: 'abc123...',
      timestamp: '2024-01-15T10:00:00',
    },
  ],

  'GET /portal/:token': {
    job_title: 'Junior Backend Developer (Python)',
    first_name: 'Sara',
    max_chars: 4000,
    application_id: 1,
    questions: [
      {
        id: 1,
        text: 'Tell us about your experience with backend systems.',
        rubric: 'Look for depth and relevant experience.',
      },
      {
        id: 2,
        text: 'Describe a time you solved a complex problem.',
        rubric: 'Assess problem-solving approach.',
      },
    ],
    token_remaining_hours: 24,
  },
}

/**
 * Delay for realistic latency simulation.
 */
const delay = (ms = 300) =>
  new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Match request to mock response.
 * Returns mock response if found, otherwise null.
 */
export async function getMockResponse(method, path) {
  const clean = path.split('?')[0].replace(/\/$/, '')
  let response = mockResponses[`${method} ${clean}`]

  // Match patterns like 'GET /emails/:id'
  if (!response) {
    const parts = clean.split('/')
    const key = Object.keys(mockResponses).find((k) => {
      const [m, p] = k.split(' ')
      const kp = p.split('/')
      return m === method && kp.length === parts.length && kp.every((seg, i) => seg.startsWith(':') || seg === parts[i])
    })
    response = key ? mockResponses[key] : null
  }

  // Any other POST in mock mode just "works"
  if (!response && method === 'POST') response = { ok: true, status: 'confirmed' }

  if (response) {
    await delay()
    return { status: 200, data: response }
  }
  return null
}

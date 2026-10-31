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
      id: 1,
      title: 'Senior Backend Engineer',
      description: 'We are hiring an experienced backend engineer.',
      rubric_json: {
        experience: { weight: 0.3 },
        technical_skills: { weight: 0.5 },
        communication: { weight: 0.2 },
      },
      rubric_approved_by: 1,
      created_at: '2024-01-15T10:00:00',
    },
  ],

  'GET /candidates': [
    {
      id: 1,
      name: 'Alice Smith',
      email: 'alice@example.com',
      status: 'SCREENED',
      score: 8.5,
    },
    {
      id: 2,
      name: 'Bob Jones',
      email: 'bob@example.com',
      status: 'SCREENED',
      score: 7.2,
    },
  ],

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

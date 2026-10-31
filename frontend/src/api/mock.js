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
    high_urgency_count: 2,
    needs_human_count: 3,
    pending_approvals_count: 5,
    pending_applications_count: 10,
    summary: 'You have 5 applications awaiting review.',
  },

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
  const key = `${method} ${path}`
  const response = mockResponses[key]

  if (response) {
    await delay()
    return {
      status: 200,
      data: response,
    }
  }

  return null
}

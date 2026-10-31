/**
 * Candidate portal (public, token-protected).
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api'

export default function Portal() {
  const { token } = useParams()
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [answers, setAnswers] = useState({})

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiGet(`/portal/${token}`)
        setSession(res.data)
        // Initialize empty answers for each question
        const init = {}
        res.data.questions.forEach(q => {
          init[q.id] = ''
        })
        setAnswers(init)
      } catch (err) {
        console.error('Failed to load portal session:', err)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [token])

  const handleAnswerChange = (qId, value) => {
    setAnswers({ ...answers, [qId]: value })
  }

  const handleSubmit = async () => {
    try {
      await apiPost(`/portal/${token}/video`, { answers })
      alert('Answers submitted successfully!')
    } catch (err) {
      console.error('Submission failed:', err)
      alert('Failed to submit')
    }
  }

  if (loading) return <div className="text-center text-gray-500">Loading...</div>

  if (!session) return <div className="text-center text-red-500">Invalid token or session expired</div>

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Interview Questions</h1>
      <p className="text-gray-600 mb-6">
        You have {session.token_remaining_hours} hours to complete this interview.
      </p>

      <div className="space-y-6">
        {session.questions.map((q) => (
          <div key={q.id} className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-semibold text-lg mb-2">{q.text}</h3>
            <p className="text-sm text-gray-600 mb-4">Rubric: {q.rubric}</p>
            <textarea
              value={answers[q.id] || ''}
              onChange={(e) => handleAnswerChange(q.id, e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 h-32"
              placeholder="Type your answer here..."
            />
          </div>
        ))}
      </div>

      <button
        onClick={handleSubmit}
        className="mt-6 w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700"
      >
        Submit Answers
      </button>
    </div>
  )
}

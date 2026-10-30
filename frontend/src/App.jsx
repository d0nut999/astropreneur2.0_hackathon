import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [users, setUsers] = useState([])
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    full_name: '',
    password: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Fetch users on component mount
  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      const response = await axios.get('/api/users')
      setUsers(response.data)
    } catch (err) {
      setError('Failed to fetch users: ' + err.message)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      await axios.post('/api/users', formData)
      setFormData({
        email: '',
        username: '',
        full_name: '',
        password: ''
      })
      fetchUsers()
      alert('User created successfully!')
    } catch (err) {
      setError('Failed to create user: ' + err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await axios.delete(`/api/users/${userId}`)
        fetchUsers()
      } catch (err) {
        setError('Failed to delete user: ' + err.message)
      }
    }
  }

  return (
    <div className='app'>
      <header className='header'>
        <h1>Hackathon User Manager</h1>
      </header>

      <main className='main'>
        <div className='container'>
          {/* Form Section */}
          <section className='form-section'>
            <h2>Create New User</h2>
            {error && <div className='error'>{error}</div>}
            <form onSubmit={handleSubmit} className='user-form'>
              <div className='form-group'>
                <label htmlFor='email'>Email:</label>
                <input
                  type='email'
                  id='email'
                  name='email'
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className='form-group'>
                <label htmlFor='username'>Username:</label>
                <input
                  type='text'
                  id='username'
                  name='username'
                  value={formData.username}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className='form-group'>
                <label htmlFor='full_name'>Full Name:</label>
                <input
                  type='text'
                  id='full_name'
                  name='full_name'
                  value={formData.full_name}
                  onChange={handleInputChange}
                />
              </div>

              <div className='form-group'>
                <label htmlFor='password'>Password:</label>
                <input
                  type='password'
                  id='password'
                  name='password'
                  value={formData.password}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <button type='submit' disabled={loading}>
                {loading ? 'Creating...' : 'Create User'}
              </button>
            </form>
          </section>

          {/* Users List Section */}
          <section className='users-section'>
            <h2>Users List</h2>
            {users.length === 0 ? (
              <p>No users found. Create one to get started!</p>
            ) : (
              <div className='users-grid'>
                {users.map(user => (
                  <div key={user.id} className='user-card'>
                    <h3>{user.username}</h3>
                    <p><strong>Email:</strong> {user.email}</p>
                    <p><strong>Name:</strong> {user.full_name || 'N/A'}</p>
                    <p><strong>Status:</strong> {user.is_active ? 'Active' : 'Inactive'}</p>
                    <p><strong>Created:</strong> {new Date(user.created_at).toLocaleDateString()}</p>
                    <button
                      className='delete-btn'
                      onClick={() => handleDelete(user.id)}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

export default App

import React, { useState, useEffect, useRef } from 'react';
import { Send, LogOut, User, Mail, Lock, UserPlus, LogIn, MessageCircle, Paperclip, X } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://takeashot-backend.onrender.com/api';

const App = () => {
  const [currentView, setCurrentView] = useState('login');
  const [currentUser, setCurrentUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [signupForm, setSignupForm] = useState({ full_name: '', email: '', password: '', role: 'employee' });
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (token) {
      loadCurrentUser();
    }
  }, [token]);

  useEffect(() => {
    if (currentUser && token) {
      loadChatHistory();
    }
  }, [currentUser]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadCurrentUser = async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const user = await response.json();
        setCurrentUser(user);
        setCurrentView('chat');
      } else {
        handleLogout();
      }
    } catch (error) {
      console.error('Error loading user:', error);
      handleLogout();
    }
  };

  const loadChatHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/chat/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        const historyArray = data.history || data || [];
        setMessages(Array.isArray(historyArray) ? historyArray : []);
      } else {
        setMessages([]);
      }
    } catch (error) {
      console.error('Error loading chat:', error);
      setMessages([]);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm)
      });
      if (response.ok) {
        const data = await response.json();
        setToken(data.access_token);
        localStorage.setItem('token', data.access_token);
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Login failed');
      }
    } catch (error) {
      setError('Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signupForm)
      });
      if (response.ok) {
        alert('Account created! Please login.');
        setCurrentView('login');
        setLoginForm({ email: signupForm.email, password: '' });
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Signup failed');
      }
    } catch (error) {
      setError('Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setCurrentUser(null);
    setMessages([]);
    localStorage.removeItem('token');
    setCurrentView('login');
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const messageText = inputMessage.trim();
    
    if (!messageText) return;
    if (loading) return;
    
    setLoading(true);
    setError('');
    
    const userMsg = {
      sender_id: currentUser.id,
      receiver_id: null,
      content: messageText,
      file_path: null,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    
    try {
      const response = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: currentUser.id,
          message: messageText,
          file_path: null,
          filename: null
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        const aiMsg = {
          sender_id: null,
          receiver_id: currentUser.id,
          content: data.response,
          file_path: null,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, aiMsg]);
      } else {
        setError(`Failed to send message (${response.status})`);
      }
    } catch (error) {
      setError('Network error. Check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (file.size > 10 * 1024 * 1024) {
      setError('File too large (max 10MB)');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    
    setUploading(true);
    setLoading(true);
    setError('');
    
    const originalFileName = file.name;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', currentUser.id.toString());
    
    try {
      const response = await fetch(`${API_BASE}/upload/file`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Add file message to chat
        const userMsg = {
          sender_id: currentUser.id,
          content: `📎 ${originalFileName}`,
          file_path: data.file_url,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, userMsg]);
        
        // Send to AI
        const aiResponse = await fetch(`${API_BASE}/chat/message`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            user_id: currentUser.id,
            message: `uploaded file: ${originalFileName}`,
            file_path: data.file_url,
            filename: originalFileName
          })
        });
        
        if (aiResponse.ok) {
          const aiData = await aiResponse.json();
          setMessages(prev => [...prev, {
            sender_id: null,
            content: aiData.response,
            timestamp: new Date().toISOString()
          }]);
        }
      } else {
        setError('Upload failed');
      }
    } catch (error) {
      setError('Upload error');
    } finally {
      setUploading(false);
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDownloadFile = async (fileUrl, messageContent) => {
    try {
      // Extract original filename from message "📎 filename.pdf"
      let fileName = 'download';
      if (messageContent && messageContent.includes('📎')) {
        fileName = messageContent.replace('📎', '').trim();
      }
      
      const response = await fetch(fileUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(link);
      }, 100);
    } catch (error) {
      window.open(fileUrl, '_blank');
    }
  };

  // LOGIN VIEW
  if (currentView === 'login') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 50%, #0a0a0a 100%)' }}>
        <div style={{ background: 'white', padding: '2rem', borderRadius: '1rem', boxShadow: '0 20px 60px rgba(0,0,0,0.5)', width: '90%', maxWidth: '400px' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div style={{ width: '4rem', height: '4rem', background: 'linear-gradient(135deg, #1a1a1a 0%, #333 100%)', borderRadius: '50%', margin: '0 auto 1rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <LogIn style={{ color: 'white', width: '2rem', height: '2rem' }} />
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', marginBottom: '0.5rem' }}>Welcome Back</h2>
            <p style={{ color: '#6b7280' }}>Sign in to Take a Shot</p>
          </div>
          {error && <div style={{ padding: '0.75rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '0.5rem', marginBottom: '1rem', color: '#dc2626', fontSize: '0.875rem' }}>{error}</div>}
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Email</label>
              <div style={{ position: 'relative' }}>
                <Mail style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af', width: '1.25rem', height: '1.25rem' }} />
                <input type="email" value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} style={{ width: '100%', padding: '0.75rem 0.75rem 0.75rem 2.5rem', border: '1px solid #d1d5db', borderRadius: '0.5rem', fontSize: '1rem', boxSizing: 'border-box' }} placeholder="your@email.com" required />
              </div>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Password</label>
              <div style={{ position: 'relative' }}>
                <Lock style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af', width: '1.25rem', height: '1.25rem' }} />
                <input type="password" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} style={{ width: '100%', padding: '0.75rem 0.75rem 0.75rem 2.5rem', border: '1px solid #d1d5db', borderRadius: '0.5rem', fontSize: '1rem', boxSizing: 'border-box' }} placeholder="••••••••" required />
              </div>
            </div>
            <button type="submit" disabled={loading} style={{ background: 'linear-gradient(135deg, #1a1a1a 0%, #333 100%)', color: 'white', padding: '0.75rem', borderRadius: '0.5rem', fontWeight: '600', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              <LogIn style={{ width: '1.25rem', height: '1.25rem' }} />
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          <p style={{ textAlign: 'center', marginTop: '1.5rem', color: '#6b7280', fontSize: '0.875rem' }}>
            Don't have an account? <button onClick={() => { setCurrentView('signup'); setError(''); }} style={{ color: '#1a1a1a', fontWeight: '600', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>Sign Up</button>
          </p>
        </div>
      </div>
    );
  }

  // SIGNUP VIEW
  if (currentView === 'signup') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 50%, #0a0a0a 100%)' }}>
        <div style={{ background: 'white', padding: '2rem', borderRadius: '1rem', boxShadow: '0 20px 60px rgba(0,0,0,0.5)', width: '90%', maxWidth: '400px' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div style={{ width: '4rem', height: '4rem', background: 'linear-gradient(135deg, #1a1a1a 0%, #333 100%)', borderRadius: '50%', margin: '0 auto 1rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <UserPlus style={{ color: 'white', width: '2rem', height: '2rem' }} />
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', marginBottom: '0.5rem' }}>Create Account</h2>
            <p style={{ color: '#6b7280' }}>Join Take a Shot</p>
          </div>
          {error && <div style={{ padding: '0.75rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '0.5rem', marginBottom: '1rem', color: '#dc2626', fontSize: '0.875rem' }}>{error}</div>}
          <form onSubmit={handleSignup} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Full Name</label>
              <input type="text" value={signupForm.full_name} onChange={(e) => setSignupForm({ ...signupForm, full_name: e.target.value })} style={{ width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.5rem', boxSizing: 'border-box' }} required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Email</label>
              <input type="email" value={signupForm.email} onChange={(e) => setSignupForm({ ...signupForm, email: e.target.value })} style={{ width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.5rem', boxSizing: 'border-box' }} required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Password</label>
              <input type="password" value={signupForm.password} onChange={(e) => setSignupForm({ ...signupForm, password: e.target.value })} style={{ width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.5rem', boxSizing: 'border-box' }} placeholder="Minimum 6 characters" minLength={6} required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Role</label>
              <select value={signupForm.role} onChange={(e) => setSignupForm({ ...signupForm, role: e.target.value })} style={{ width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.5rem', boxSizing: 'border-box', background: 'white' }}>
                <option value="manager">Manager</option>
                <option value="employee">Employee</option>
              </select>
            </div>
            <button type="submit" disabled={loading} style={{ background: 'linear-gradient(135deg, #1a1a1a 0%, #333 100%)', color: 'white', padding: '0.75rem', borderRadius: '0.5rem', fontWeight: '600', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}>
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>
          <p style={{ textAlign: 'center', marginTop: '1.5rem', color: '#6b7280', fontSize: '0.875rem' }}>
            Already have an account? <button onClick={() => { setCurrentView('login'); setError(''); }} style={{ color: '#1a1a1a', fontWeight: '600', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>Login</button>
          </p>
        </div>
      </div>
    );
  }

  // CHAT VIEW
  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'linear-gradient(to bottom, #f9fafb, #f3f4f6)' }}>
      {/* Header */}
      <div style={{ background: 'linear-gradient(135deg, #1a1a1a 0%, #333 100%)', color: 'white', padding: '1rem 1.5rem', boxShadow: '0 4px 6px rgba(0,0,0,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <MessageCircle style={{ width: '1.5rem', height: '1.5rem' }} />
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0 }}>Take a Shot</h1>
            <p style={{ fontSize: '0.75rem', opacity: 0.8, margin: 0 }}>AI Management Assistant</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontSize: '0.875rem', fontWeight: '600', margin: 0 }}>{currentUser?.full_name}</p>
            <p style={{ fontSize: '0.75rem', opacity: 0.8, margin: 0, textTransform: 'capitalize' }}>{currentUser?.role}</p>
          </div>
          <button onClick={handleLogout} style={{ background: 'rgba(255,255,255,0.2)', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'white', fontSize: '0.875rem', fontWeight: '500' }}>
            <LogOut style={{ width: '1rem', height: '1rem' }} />
            Logout
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          {messages.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#6b7280' }}>
              <MessageCircle style={{ width: '3rem', height: '3rem', margin: '0 auto 1rem', opacity: 0.5 }} />
              <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', color: '#374151' }}>Welcome!</h3>
              <p>Start a conversation with the AI assistant</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} style={{ display: 'flex', marginBottom: '1rem', justifyContent: msg.sender_id === null ? 'flex-start' : 'flex-end' }}>
              <div style={{ maxWidth: '75%', padding: '1rem', borderRadius: '1rem', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', background: msg.sender_id === null ? 'white' : 'linear-gradient(135deg, #1a1a1a 0%, #333 100%)', color: msg.sender_id === null ? '#1f2937' : 'white' }}>
                <div style={{ fontSize: '0.75rem', opacity: 0.7, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  {msg.sender_id === null ? <><MessageCircle style={{ width: '0.75rem', height: '0.75rem' }} /> AI Assistant</> : <><User style={{ width: '0.75rem', height: '0.75rem' }} /> You</>}
                </div>
                <div style={{ fontSize: '0.9375rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{msg.content}</div>
                {msg.file_path && (
                  <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: msg.sender_id === null ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.1)', borderRadius: '0.5rem' }}>
                    <button onClick={() => handleDownloadFile(msg.file_path, msg.content)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: msg.sender_id === null ? '#1a1a1a' : 'white', fontSize: '0.875rem', fontWeight: '600', background: 'none', border: 'none', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}>
                      <Paperclip style={{ width: '1rem', height: '1rem' }} />
                      <span style={{ textDecoration: 'underline' }}>
                        {msg.content && msg.content.includes('📎') ? msg.content.replace('📎', '').trim() : 'Download File'}
                      </span>
                    </button>
                  </div>
                )}
                <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: '0.5rem' }}>{new Date(msg.timestamp).toLocaleTimeString()}</div>
              </div>
            </div>
          ))}
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '1rem' }}>
              <div style={{ background: 'white', padding: '1rem', borderRadius: '1rem', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <div style={{ width: '0.5rem', height: '0.5rem', background: '#9ca3af', borderRadius: '50%', animation: 'pulse 1.4s ease-in-out infinite' }}></div>
                  <div style={{ width: '0.5rem', height: '0.5rem', background: '#9ca3af', borderRadius: '50%', animation: 'pulse 1.4s ease-in-out 0.2s infinite' }}></div>
                  <div style={{ width: '0.5rem', height: '0.5rem', background: '#9ca3af', borderRadius: '50%', animation: 'pulse 1.4s ease-in-out 0.4s infinite' }}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ maxWidth: '900px', margin: '0 auto', padding: '0 1.5rem 0.5rem', width: '100%', boxSizing: 'border-box' }}>
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '0.75rem', borderRadius: '0.5rem', fontSize: '0.875rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{error}</span>
            <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}>
              <X style={{ width: '1rem', height: '1rem', color: '#dc2626' }} />
            </button>
          </div>
        </div>
      )}

      {/* Input */}
      <div style={{ background: 'white', padding: '1rem 1.5rem', borderTop: '1px solid #e5e7eb', boxShadow: '0 -2px 10px rgba(0,0,0,0.05)' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '0.75rem' }}>
            <input type="file" ref={fileInputRef} onChange={handleFileSelect} style={{ display: 'none' }} />
            <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading || loading} style={{ background: '#f3f4f6', border: '1px solid #d1d5db', padding: '0.75rem', borderRadius: '0.5rem', cursor: uploading || loading ? 'not-allowed' : 'pointer', opacity: uploading || loading ? 0.5 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }} title={uploading ? 'Uploading...' : 'Attach file'}>
              <Paperclip style={{ width: '1.25rem', height: '1.25rem', color: '#6b7280' }} />
            </button>
            <input type="text" value={inputMessage} onChange={(e) => setInputMessage(e.target.value)} placeholder={uploading ? 'Uploading file...' : 'Type your message...'} disabled={loading || uploading} style={{ flex: 1, padding: '0.75rem 1rem', border: '1px solid #d1d5db', borderRadius: '0.5rem', fontSize: '1rem', outline: 'none', boxSizing: 'border-box' }} />
            <button type="submit" disabled={loading || uploading || !inputMessage.trim()} style={{ background: 'linear-gradient(135deg, #1a1a1a 0%, #333 100%)', color: 'white', padding: '0.75rem 1.5rem', borderRadius: '0.5rem', border: 'none', cursor: loading || uploading || !inputMessage.trim() ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: '600', opacity: loading || uploading || !inputMessage.trim() ? 0.5 : 1, flexShrink: 0 }}>
              <Send style={{ width: '1.25rem', height: '1.25rem' }} />
              Send
            </button>
          </form>
        </div>
      </div>
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
        input:focus { border-color: #1a1a1a !important; box-shadow: 0 0 0 2px rgba(26, 26, 26, 0.2); }
      `}</style>
    </div>
  );
};

export default App;
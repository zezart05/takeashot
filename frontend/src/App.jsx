import React, { useState, useEffect, useRef } from 'react';
import { Send, LogOut, User, Mail, Lock, UserPlus, LogIn, MessageCircle } from 'lucide-react';

const API_BASE = 'https://smooth-flowers-try.loca.lt/api';

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
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (token) {
      loadCurrentUser();
      loadChatHistory();
    }
  }, [token]);

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
        const formattedMessages = data.history.map(msg => ({
          id: msg.id,
          sender_id: msg.sender_id,
          content: msg.content,
          timestamp: msg.timestamp,
          file_path: msg.file_path
        }));
        setMessages(formattedMessages);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
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
        setCurrentUser(data.user);
        setCurrentView('chat');
        setLoginForm({ email: '', password: '' });
      } else {
        const error = await response.json();
        setError(error.detail || 'Login failed');
      }
    } catch (error) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    if (signupForm.password.length < 6) {
      setError('Password must be at least 6 characters');
      setLoading(false);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signupForm)
      });
      if (response.ok) {
        const data = await response.json();
        setToken(data.access_token);
        localStorage.setItem('token', data.access_token);
        setCurrentUser(data.user);
        setCurrentView('chat');
        setSignupForm({ full_name: '', email: '', password: '', role: 'employee' });
      } else {
        const error = await response.json();
        setError(error.detail || 'Signup failed');
      }
    } catch (error) {
      setError('Network error. Please try again.');
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

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (file.size > 10485760) {
      setError('File too large (max 10MB)');
      return;
    }
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`${API_BASE}/upload/file`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      if (response.ok) {
        const data = await response.json();
        setUploadedFile(data);
        setError('');
      } else {
        setError('File upload failed');
      }
    } catch (error) {
      setError('File upload error');
    } finally {
      setUploading(false);
    }
  };

  const removeFile = () => {
    setUploadedFile(null);
  };

  const sendMessage = async () => {
    if ((!inputMessage.trim() && !uploadedFile) || !currentUser) return;
    setLoading(true);
    
    const userMessage = {
      id: Date.now(),
      sender_id: currentUser.id,
      content: inputMessage || '(File attachment)',
      timestamp: new Date().toISOString(),
      file_path: uploadedFile?.filepath
    };
    setMessages([...messages, userMessage]);
    
    try {
      const response = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: currentUser.id,
          message: inputMessage || '(file)',
          file_path: uploadedFile?.filepath,
          filename: uploadedFile?.filename
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        const aiMessage = {
          id: Date.now() + 1,
          sender_id: null,
          content: data.response,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, aiMessage]);
        setUploadedFile(null);
        setError('');
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to send message');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
      setInputMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleDownload = async (filepath, e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/upload/file/${filepath}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filepath.split('_').slice(2).join('_') || 'download';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        setError('Failed to download file');
      }
    } catch (error) {
      console.error('Download error:', error);
      setError('Download failed');
    }
  };

  if (currentView === 'login') {
    return (
      <div style={{minHeight:'100vh',background:'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)',display:'flex',alignItems:'center',justifyContent:'center',padding:'1rem'}}>
        <div style={{background:'#ffffff',borderRadius:'1rem',boxShadow:'0 20px 40px rgba(0,0,0,0.3)',padding:'2rem',maxWidth:'28rem',width:'100%'}}>
          <div style={{textAlign:'center',marginBottom:'2rem'}}>
            <div style={{width:'5rem',height:'5rem',background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',borderRadius:'50%',display:'flex',alignItems:'center',justifyContent:'center',margin:'0 auto 1rem'}}>
              <MessageCircle style={{width:'2.5rem',height:'2.5rem',color:'white'}} />
            </div>
            <h1 style={{fontSize:'1.875rem',fontWeight:'bold',color:'#1f2937',marginBottom:'0.5rem'}}>Take a Shot</h1>
            <p style={{color:'#6b7280'}}>AI Management Assistant</p>
          </div>
          
          {error && <div style={{background:'#fee',border:'1px solid #fcc',color:'#c00',padding:'0.75rem 1rem',borderRadius:'0.5rem',marginBottom:'1rem',fontSize:'0.875rem'}}>{error}</div>}
          
          <form onSubmit={handleLogin} style={{display:'flex',flexDirection:'column',gap:'1rem'}}>
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Email</label>
              <div style={{position:'relative'}}>
                <Mail style={{position:'absolute',left:'0.75rem',top:'50%',transform:'translateY(-50%)',color:'#9ca3af',width:'1.25rem',height:'1.25rem'}} />
                <input type="email" value={loginForm.email} onChange={(e) => setLoginForm({...loginForm, email: e.target.value})} style={{width:'100%',paddingLeft:'2.5rem',paddingRight:'1rem',paddingTop:'0.75rem',paddingBottom:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem',outline:'none'}} placeholder="your.email@example.com" required />
              </div>
            </div>
            
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Password</label>
              <div style={{position:'relative'}}>
                <Lock style={{position:'absolute',left:'0.75rem',top:'50%',transform:'translateY(-50%)',color:'#9ca3af',width:'1.25rem',height:'1.25rem'}} />
                <input type="password" value={loginForm.password} onChange={(e) => setLoginForm({...loginForm, password: e.target.value})} style={{width:'100%',paddingLeft:'2.5rem',paddingRight:'1rem',paddingTop:'0.75rem',paddingBottom:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem',outline:'none'}} placeholder="••••••••" required />
              </div>
            </div>
            
            <button type="submit" disabled={loading} style={{width:'100%',background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',color:'white',padding:'0.75rem',borderRadius:'0.5rem',fontWeight:'600',border:'none',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.5rem'}}>
              {loading ? <div style={{width:'1.5rem',height:'1.5rem',border:'2px solid white',borderTopColor:'transparent',borderRadius:'50%',animation:'spin 1s linear infinite'}} /> : <><LogIn style={{width:'1.25rem',height:'1.25rem'}} /> Login</>}
            </button>
          </form>
          
          <div style={{marginTop:'1.5rem',textAlign:'center'}}>
            <p style={{color:'#6b7280'}}>Don't have an account? <button onClick={() => {setCurrentView('signup');setError('');}} style={{color:'#1a1a1a',fontWeight:'600',background:'none',border:'none',cursor:'pointer'}}>Sign up</button></p>
          </div>
          
          <div style={{marginTop:'1.5rem',padding:'1rem',background:'#f9fafb',borderRadius:'0.5rem'}}>
            <p style={{fontSize:'0.75rem',color:'#6b7280',textAlign:'center',marginBottom:'0.5rem'}}>Demo Credentials:</p>
            <p style={{fontSize:'0.75rem',color:'#6b7280'}}>Manager: manager@takeashot.com / password123</p>
            <p style={{fontSize:'0.75rem',color:'#6b7280'}}>Employee: alex.johnson@takeashot.com / password123</p>
          </div>
        </div>
      </div>
    );
  }

  if (currentView === 'signup') {
    return (
      <div style={{minHeight:'100vh',background:'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)',display:'flex',alignItems:'center',justifyContent:'center',padding:'1rem'}}>
        <div style={{background:'white',borderRadius:'1rem',boxShadow:'0 20px 40px rgba(0,0,0,0.3)',padding:'2rem',maxWidth:'28rem',width:'100%'}}>
          <div style={{textAlign:'center',marginBottom:'2rem'}}>
            <div style={{width:'5rem',height:'5rem',background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',borderRadius:'50%',display:'flex',alignItems:'center',justifyContent:'center',margin:'0 auto 1rem'}}>
              <UserPlus style={{width:'2.5rem',height:'2.5rem',color:'white'}} />
            </div>
            <h1 style={{fontSize:'1.875rem',fontWeight:'bold',color:'#1f2937',marginBottom:'0.5rem'}}>Create Account</h1>
            <p style={{color:'#6b7280'}}>Join Take a Shot</p>
          </div>
          
          {error && <div style={{background:'#fee',border:'1px solid #fcc',color:'#c00',padding:'0.75rem 1rem',borderRadius:'0.5rem',marginBottom:'1rem',fontSize:'0.875rem'}}>{error}</div>}
          
          <form onSubmit={handleSignup} style={{display:'flex',flexDirection:'column',gap:'1rem'}}>
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Full Name</label>
              <input type="text" value={signupForm.full_name} onChange={(e) => setSignupForm({...signupForm, full_name: e.target.value})} style={{width:'100%',padding:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem',outline:'none'}} placeholder="John Doe" required />
            </div>
            
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Email</label>
              <input type="email" value={signupForm.email} onChange={(e) => setSignupForm({...signupForm, email: e.target.value})} style={{width:'100%',padding:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem',outline:'none'}} placeholder="your.email@example.com" required />
            </div>
            
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Password</label>
              <input type="password" value={signupForm.password} onChange={(e) => setSignupForm({...signupForm, password: e.target.value})} style={{width:'100%',padding:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem',outline:'none'}} placeholder="••••••••" required minLength={6} />
              <p style={{fontSize:'0.75rem',color:'#6b7280',marginTop:'0.25rem'}}>Minimum 6 characters</p>
            </div>
            
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Role</label>
              <select value={signupForm.role} onChange={(e) => setSignupForm({...signupForm, role: e.target.value})} style={{width:'100%',padding:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem',outline:'none'}}>
                <option value="employee">Employee</option>
                <option value="manager">Manager</option>
              </select>
            </div>
            
            <button type="submit" disabled={loading} style={{width:'100%',background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',color:'white',padding:'0.75rem',borderRadius:'0.5rem',fontWeight:'600',border:'none',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.5rem'}}>
              {loading ? <div style={{width:'1.5rem',height:'1.5rem',border:'2px solid white',borderTopColor:'transparent',borderRadius:'50%',animation:'spin 1s linear infinite'}} /> : <><UserPlus style={{width:'1.25rem',height:'1.25rem'}} /> Create Account</>}
            </button>
          </form>
          
          <div style={{marginTop:'1.5rem',textAlign:'center'}}>
            <p style={{color:'#6b7280'}}>Already have an account? <button onClick={() => {setCurrentView('login');setError('');}} style={{color:'#1a1a1a',fontWeight:'600',background:'none',border:'none',cursor:'pointer'}}>Login</button></p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{minHeight:'100vh',background:'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)'}}>
      <div style={{maxWidth:'1280px',margin:'0 auto',padding:'1rem'}}>
        <div style={{background:'white',borderRadius:'1rem',boxShadow:'0 20px 40px rgba(0,0,0,0.3)',overflow:'hidden'}}>
          <div style={{background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',padding:'1.5rem',color:'white'}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <div>
                <h1 style={{fontSize:'1.5rem',fontWeight:'bold',marginBottom:'0.25rem',display:'flex',alignItems:'center',gap:'0.5rem'}}><MessageCircle style={{width:'1.5rem',height:'1.5rem'}} /> Take a Shot</h1>
                <p style={{fontSize:'0.875rem',opacity:0.9}}>AI Management Assistant</p>
              </div>
              <div style={{textAlign:'right'}}>
                <div style={{display:'flex',alignItems:'center',gap:'0.5rem',justifyContent:'flex-end',marginBottom:'0.25rem'}}>
                  <User style={{width:'1.25rem',height:'1.25rem'}} />
                  <span style={{fontWeight:'600'}}>{currentUser?.full_name}</span>
                </div>
                <div style={{fontSize:'0.875rem',opacity:0.9,textTransform:'capitalize',marginBottom:'0.5rem'}}>{currentUser?.role}</div>
                <button onClick={handleLogout} style={{fontSize:'0.75rem',background:'rgba(255,255,255,0.2)',padding:'0.25rem 0.75rem',borderRadius:'9999px',border:'none',color:'white',cursor:'pointer',display:'flex',alignItems:'center',gap:'0.25rem'}}>
                  <LogOut style={{width:'0.75rem',height:'0.75rem'}} /> Logout
                </button>
              </div>
            </div>
          </div>
          
          <div style={{padding:'1.5rem',height:'600px',overflowY:'auto',background:'#f9fafb'}}>
            {messages.length === 0 && (
              <div style={{textAlign:'center',color:'#6b7280',marginTop:'5rem'}}>
                <MessageCircle style={{width:'4rem',height:'4rem',margin:'0 auto 1rem',color:'#d1d5db'}} />
                <p style={{fontSize:'1.125rem',fontWeight:'600',marginBottom:'0.5rem'}}>Welcome to Take a Shot!</p>
                <p style={{fontSize:'0.875rem'}}>{currentUser?.role === 'manager' ? "Say 'give a task' to start assigning work" : "Say 'my tasks' to see your assignments"}</p>
              </div>
            )}
            
            {messages.map((msg, idx) => (
              <div key={idx} style={{display:'flex',marginBottom:'1rem',justifyContent:msg.sender_id===null?'flex-start':'flex-end'}}>
                <div style={{maxWidth:'75%',padding:'1rem',borderRadius:'1rem',boxShadow:'0 2px 4px rgba(0,0,0,0.1)',background:msg.sender_id===null?'white':'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',color:msg.sender_id===null?'#1f2937':'white'}}>
                  <div style={{fontSize:'0.75rem',opacity:0.7,marginBottom:'0.25rem',display:'flex',alignItems:'center',gap:'0.25rem'}}>
                    {msg.sender_id===null?<><MessageCircle style={{width:'0.75rem',height:'0.75rem'}} /> AI Assistant</>:<><User style={{width:'0.75rem',height:'0.75rem'}} /> You</>}
                  </div>
                  <div style={{fontSize:'0.875rem',lineHeight:1.6,whiteSpace:'pre-wrap'}}>{msg.content}</div>
                  {msg.file_path && (
                    <div style={{marginTop:'0.75rem',padding:'0.75rem',background:'rgba(0,0,0,0.1)',borderRadius:'0.5rem',display:'flex',alignItems:'center',gap:'0.5rem'}}>
                      <span style={{fontSize:'1.25rem'}}>📎</span>
                      <button 
                        onClick={(e) => handleDownload(msg.file_path, e)}
                        style={{color:msg.sender_id===null?'#1a1a1a':'white',fontSize:'0.875rem',textDecoration:'underline',fontWeight:'600',flex:1,background:'none',border:'none',cursor:'pointer',textAlign:'left'}}
                      >
                        Download Attachment
                      </button>
                    </div>
                  )}
                  <div style={{fontSize:'0.75rem',opacity:0.6,marginTop:'0.5rem'}}>{new Date(msg.timestamp).toLocaleTimeString()}</div>
                </div>
              </div>
            ))}
            
            {loading && (
              <div style={{display:'flex',justifyContent:'flex-start',marginBottom:'1rem'}}>
                <div style={{background:'white',border:'1px solid #e5e7eb',padding:'1rem',borderRadius:'1rem',boxShadow:'0 2px 4px rgba(0,0,0,0.1)'}}>
                  <div style={{display:'flex',gap:'0.5rem'}}>
                    <div style={{width:'0.5rem',height:'0.5rem',background:'#9ca3af',borderRadius:'50%',animation:'bounce 1s infinite'}} />
                    <div style={{width:'0.5rem',height:'0.5rem',background:'#9ca3af',borderRadius:'50%',animation:'bounce 1s infinite 0.1s'}} />
                    <div style={{width:'0.5rem',height:'0.5rem',background:'#9ca3af',borderRadius:'50%',animation:'bounce 1s infinite 0.2s'}} />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
          
          <div style={{padding:'1rem',background:'white',borderTop:'1px solid #e5e7eb'}}>
            {error && <div style={{background:'#fee',border:'1px solid #fcc',color:'#c00',padding:'0.5rem 1rem',borderRadius:'0.5rem',marginBottom:'0.75rem',fontSize:'0.875rem'}}>{error}</div>}
            
            {uploadedFile && (
              <div style={{background:'#f0fdf4',border:'1px solid #86efac',padding:'0.75rem 1rem',borderRadius:'0.5rem',marginBottom:'0.75rem',display:'flex',justifyContent:'space-between',alignItems:'center',boxShadow:'0 2px 4px rgba(0,0,0,0.05)'}}>
                <div style={{display:'flex',alignItems:'center',gap:'0.5rem'}}>
                  <span style={{fontSize:'1.5rem'}}>📎</span>
                  <div>
                    <div style={{fontSize:'0.875rem',fontWeight:'600',color:'#166534'}}>{uploadedFile.filename}</div>
                    <div style={{fontSize:'0.75rem',color:'#16a34a'}}>{(uploadedFile.size / 1024).toFixed(1)} KB</div>
                  </div>
                </div>
                <button onClick={removeFile} style={{background:'#ef4444',color:'white',padding:'0.5rem 0.75rem',borderRadius:'0.5rem',border:'none',cursor:'pointer',fontSize:'0.75rem',fontWeight:'600',boxShadow:'0 2px 4px rgba(0,0,0,0.1)'}}>✕ Remove</button>
              </div>
            )}
            
            <div style={{display:'flex',gap:'0.5rem',alignItems:'stretch'}}>
              <label style={{display:'flex',alignItems:'center',justifyContent:'center',padding:'0.75rem 1rem',border:'2px solid #d1d5db',borderRadius:'0.75rem',cursor:uploading||loading?'not-allowed':'pointer',background:uploading||loading?'#f3f4f6':'white',transition:'all 0.2s'}}>
                <input type="file" onChange={handleFileUpload} style={{display:'none'}} disabled={uploading || loading} />
                <span style={{fontSize:'1.5rem'}}>{uploading ? '⏳' : '📎'}</span>
              </label>
              
              <input type="text" value={inputMessage} onChange={(e) => setInputMessage(e.target.value)} onKeyPress={handleKeyPress} placeholder={uploadedFile ? "Add message and send..." : "Type your message..."} disabled={loading} style={{flex:1,padding:'0.75rem 1rem',border:'2px solid #d1d5db',borderRadius:'0.75rem',outline:'none',fontSize:'0.875rem'}} />
              
              <button onClick={sendMessage} disabled={loading || (!inputMessage.trim() && !uploadedFile)} style={{background:loading||(!inputMessage.trim()&&!uploadedFile)?'#9ca3af':'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',color:'white',padding:'0.75rem 1.25rem',borderRadius:'0.75rem',border:'none',cursor:loading||(!inputMessage.trim()&&!uploadedFile)?'not-allowed':'pointer',boxShadow:'0 4px 6px -1px rgba(0,0,0,0.1)',transition:'all 0.2s'}}>
                <Send style={{width:'1.25rem',height:'1.25rem'}} />
              </button>
            </div>
            
            <div style={{marginTop:'0.75rem',fontSize:'0.75rem',color:'#6b7280',textAlign:'center'}}>
              {currentUser?.role === 'manager' ? "Try: 'give a task' • 'show tasks' • 'send feedback'" : "Try: 'my tasks' • 'complete task' • 'question'"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
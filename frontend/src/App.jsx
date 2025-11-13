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
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [fileComment, setFileComment] = useState('');
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

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
        setMessages(data);
      }
    } catch (error) {
      console.error('Error loading chat:', error);
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
        setCurrentView('chat');
      } else {
        const errorData = await response.json();
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
        setError('');
        setCurrentView('login');
        setLoginForm({ email: signupForm.email, password: '' });
      } else {
        const errorData = await response.json();
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
    
    let messageText = inputMessage.trim();
    let fileData = uploadedFile;
    
    // If no text and no file, don't send
    if (!messageText && !fileData) return;
    
    // If there's a file, use the comment as message text
    if (fileData && fileComment) {
      messageText = fileComment;
    }
    
    setLoading(true);
    setError('');
    
    // Add user message to UI immediately
    const userMsg = {
      sender_id: currentUser.id,
      receiver_id: null,
      content: messageText || (fileData ? `📎 ${fileData.filename}` : ''),
      file_path: fileData ? fileData.file_url : null,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMsg]);
    
    // Clear inputs
    setInputMessage('');
    setFileComment('');
    setUploadedFile(null);
    
    try {
      // Send message to backend
      const response = await fetch(`${API_BASE}/chat/send`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sender_id: currentUser.id,
          content: messageText || `uploaded file: ${fileData?.filename || 'file'}`,
          file_path: fileData ? fileData.file_url : null
        })
      });
      
      if (response.ok) {
        // Reload chat to get AI response
        setTimeout(() => loadChatHistory(), 1500);
      } else {
        setError('Failed to send message');
      }
    } catch (error) {
      console.error('Send error:', error);
      setError('Error sending message');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (file.size > 10485760) {
      setError('File too large (max 10MB)');
      return;
    }
    
    setUploading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', currentUser.id);
    
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
        setError('Upload failed. Please try again.');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setError('Upload error. Please try again.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDownloadFile = async (fileUrl, fileName) => {
    try {
      const response = await fetch(fileUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName || 'download';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
      // Fallback: open in new tab
      window.open(fileUrl, '_blank');
    }
  };

  const cancelFileUpload = () => {
    setUploadedFile(null);
    setFileComment('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (currentView === 'login') {
    return (
      <div style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'}}>
        <div style={{background:'white',padding:'2rem',borderRadius:'1rem',boxShadow:'0 10px 25px rgba(0,0,0,0.2)',width:'90%',maxWidth:'400px'}}>
          <div style={{textAlign:'center',marginBottom:'2rem'}}>
            <div style={{width:'4rem',height:'4rem',background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',borderRadius:'50%',margin:'0 auto 1rem',display:'flex',alignItems:'center',justifyContent:'center'}}>
              <LogIn style={{color:'white',width:'2rem',height:'2rem'}} />
            </div>
            <h2 style={{fontSize:'1.5rem',fontWeight:'bold',color:'#1f2937',marginBottom:'0.5rem'}}>Welcome Back</h2>
            <p style={{color:'#6b7280'}}>Sign in to Take a Shot</p>
          </div>
          
          {error && <div style={{padding:'0.75rem',background:'#fee',border:'1px solid #fcc',borderRadius:'0.5rem',marginBottom:'1rem',color:'#c00'}}>{error}</div>}
          
          <form onSubmit={handleLogin} style={{display:'flex',flexDirection:'column',gap:'1rem'}}>
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Email</label>
              <div style={{position:'relative'}}>
                <Mail style={{position:'absolute',left:'0.75rem',top:'50%',transform:'translateY(-50%)',color:'#9ca3af',width:'1.25rem',height:'1.25rem'}} />
                <input type="email" value={loginForm.email} onChange={(e)=>setLoginForm({...loginForm,email:e.target.value})} style={{width:'100%',padding:'0.75rem 0.75rem 0.75rem 2.5rem',border:'1px solid #d1d5db',borderRadius:'0.5rem',fontSize:'1rem'}} placeholder="your@email.com" required />
              </div>
            </div>
            
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Password</label>
              <div style={{position:'relative'}}>
                <Lock style={{position:'absolute',left:'0.75rem',top:'50%',transform:'translateY(-50%)',color:'#9ca3af',width:'1.25rem',height:'1.25rem'}} />
                <input type="password" value={loginForm.password} onChange={(e)=>setLoginForm({...loginForm,password:e.target.value})} style={{width:'100%',padding:'0.75rem 0.75rem 0.75rem 2.5rem',border:'1px solid #d1d5db',borderRadius:'0.5rem',fontSize:'1rem'}} placeholder="••••••••" required />
              </div>
            </div>
            
            <button type="submit" disabled={loading} style={{background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',color:'white',padding:'0.75rem',borderRadius:'0.5rem',fontWeight:'600',border:'none',cursor:loading?'not-allowed':'pointer',opacity:loading?0.7:1,display:'flex',alignItems:'center',justifyContent:'center',gap:'0.5rem'}}>
              <LogIn style={{width:'1.25rem',height:'1.25rem'}} />
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          
          <p style={{textAlign:'center',marginTop:'1.5rem',color:'#6b7280',fontSize:'0.875rem'}}>
            Don't have an account? <button onClick={()=>setCurrentView('signup')} style={{color:'#1a1a1a',fontWeight:'600',background:'none',border:'none',cursor:'pointer',textDecoration:'underline'}}>Sign Up</button>
          </p>
        </div>
      </div>
    );
  }

  if (currentView === 'signup') {
    return (
      <div style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'}}>
        <div style={{background:'white',padding:'2rem',borderRadius:'1rem',boxShadow:'0 10px 25px rgba(0,0,0,0.2)',width:'90%',maxWidth:'400px'}}>
          <div style={{textAlign:'center',marginBottom:'2rem'}}>
            <div style={{width:'4rem',height:'4rem',background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',borderRadius:'50%',margin:'0 auto 1rem',display:'flex',alignItems:'center',justifyContent:'center'}}>
              <UserPlus style={{color:'white',width:'2rem',height:'2rem'}} />
            </div>
            <h2 style={{fontSize:'1.5rem',fontWeight:'bold',color:'#1f2937',marginBottom:'0.5rem'}}>Create Account</h2>
            <p style={{color:'#6b7280'}}>Join Take a Shot</p>
          </div>
          
          {error && <div style={{padding:'0.75rem',background:'#fee',border:'1px solid #fcc',borderRadius:'0.5rem',marginBottom:'1rem',color:'#c00'}}>{error}</div>}
          
          <form onSubmit={handleSignup} style={{display:'flex',flexDirection:'column',gap:'1rem'}}>
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Full Name</label>
              <input type="text" value={signupForm.full_name} onChange={(e)=>setSignupForm({...signupForm,full_name:e.target.value})} style={{width:'100%',padding:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem'}} required />
            </div>
            
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Email</label>
              <input type="email" value={signupForm.email} onChange={(e)=>setSignupForm({...signupForm,email:e.target.value})} style={{width:'100%',padding:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem'}} required />
            </div>
            
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Password</label>
              <input type="password" value={signupForm.password} onChange={(e)=>setSignupForm({...signupForm,password:e.target.value})} style={{width:'100%',padding:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem'}} placeholder="Minimum 6 characters" required />
            </div>
            
            <div>
              <label style={{display:'block',fontSize:'0.875rem',fontWeight:'500',color:'#374151',marginBottom:'0.5rem'}}>Role</label>
              <select value={signupForm.role} onChange={(e)=>setSignupForm({...signupForm,role:e.target.value})} style={{width:'100%',padding:'0.75rem',border:'1px solid #d1d5db',borderRadius:'0.5rem'}}>
                <option value="manager">Manager</option>
                <option value="employee">Employee</option>
              </select>
            </div>
            
            <button type="submit" disabled={loading} style={{background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',color:'white',padding:'0.75rem',borderRadius:'0.5rem',fontWeight:'600',border:'none',cursor:loading?'not-allowed':'pointer',opacity:loading?0.7:1}}>
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>
          
          <p style={{textAlign:'center',marginTop:'1.5rem',color:'#6b7280',fontSize:'0.875rem'}}>
            Already have an account? <button onClick={()=>setCurrentView('login')} style={{color:'#1a1a1a',fontWeight:'600',background:'none',border:'none',cursor:'pointer',textDecoration:'underline'}}>Login</button>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{height:'100vh',display:'flex',flexDirection:'column',background:'linear-gradient(to bottom, #f9fafb, #f3f4f6)'}}>
      {/* Header */}
      <div style={{background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',color:'white',padding:'1rem 1.5rem',boxShadow:'0 2px 4px rgba(0,0,0,0.1)',display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div style={{display:'flex',alignItems:'center',gap:'0.75rem'}}>
          <MessageCircle style={{width:'1.5rem',height:'1.5rem'}} />
          <div>
            <h1 style={{fontSize:'1.25rem',fontWeight:'bold'}}>Take a Shot</h1>
            <p style={{fontSize:'0.75rem',opacity:0.8}}>AI Management Assistant</p>
          </div>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:'1rem'}}>
          <div style={{textAlign:'right'}}>
            <p style={{fontSize:'0.875rem',fontWeight:'600'}}>{currentUser?.full_name}</p>
            <p style={{fontSize:'0.75rem',opacity:0.8,textTransform:'capitalize'}}>{currentUser?.role}</p>
          </div>
          <button onClick={handleLogout} style={{background:'rgba(255,255,255,0.2)',padding:'0.5rem',borderRadius:'0.5rem',border:'none',cursor:'pointer',display:'flex',alignItems:'center',gap:'0.5rem',color:'white',fontSize:'0.875rem',fontWeight:'500',transition:'background 0.2s'}}>
            <LogOut style={{width:'1rem',height:'1rem'}} />
            Logout
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{flex:1,overflowY:'auto',padding:'1.5rem'}}>
        <div style={{maxWidth:'900px',margin:'0 auto'}}>
          {messages.map((msg, idx) => (
            <div key={idx} style={{display:'flex',marginBottom:'1rem',justifyContent:msg.sender_id===null?'flex-start':'flex-end'}}>
              <div style={{maxWidth:'75%',padding:'1rem',borderRadius:'1rem',boxShadow:'0 2px 4px rgba(0,0,0,0.1)',background:msg.sender_id===null?'white':'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',color:msg.sender_id===null?'#1f2937':'white'}}>
                <div style={{fontSize:'0.75rem',opacity:0.7,marginBottom:'0.25rem',display:'flex',alignItems:'center',gap:'0.25rem'}}>
                  {msg.sender_id===null?<><MessageCircle style={{width:'0.75rem',height:'0.75rem'}} /> AI Assistant</>:<><User style={{width:'0.75rem',height:'0.75rem'}} /> You</>}
                </div>
                <div style={{fontSize:'0.875rem',lineHeight:1.6,whiteSpace:'pre-wrap'}}>{msg.content}</div>
                {msg.file_path && (
                  <div style={{marginTop:'0.75rem',padding:'0.75rem',background:'rgba(0,0,0,0.1)',borderRadius:'0.5rem'}}>
                    <button 
                      onClick={() => handleDownloadFile(msg.file_path, msg.content.replace('📎', '').trim())}
                      style={{
                        display:'flex',
                        alignItems:'center',
                        gap:'0.5rem',
                        color:msg.sender_id===null?'#1a1a1a':'white',
                        fontSize:'0.875rem',
                        fontWeight:'600',
                        background:'none',
                        border:'none',
                        cursor:'pointer',
                        width:'100%',
                        textAlign:'left'
                      }}
                    >
                      <span style={{fontSize:'1.25rem'}}>📎</span>
                      <span style={{textDecoration:'underline'}}>
                        {msg.content.includes('📎') ? msg.content.replace('📎', '').trim() : 'Download File'}
                      </span>
                    </button>
                  </div>
                )}
                <div style={{fontSize:'0.75rem',opacity:0.6,marginTop:'0.5rem'}}>{new Date(msg.timestamp).toLocaleTimeString()}</div>
              </div>
            </div>
          ))}
          {loading && (
            <div style={{display:'flex',justifyContent:'flex-start',marginBottom:'1rem'}}>
              <div style={{background:'white',padding:'1rem',borderRadius:'1rem',boxShadow:'0 2px 4px rgba(0,0,0,0.1)'}}>
                <div style={{display:'flex',gap:'0.5rem'}}>
                  <div style={{width:'0.5rem',height:'0.5rem',background:'#9ca3af',borderRadius:'50%',animation:'pulse 1.4s ease-in-out infinite'}}></div>
                  <div style={{width:'0.5rem',height:'0.5rem',background:'#9ca3af',borderRadius:'50%',animation:'pulse 1.4s ease-in-out 0.2s infinite'}}></div>
                  <div style={{width:'0.5rem',height:'0.5rem',background:'#9ca3af',borderRadius:'50%',animation:'pulse 1.4s ease-in-out 0.4s infinite'}}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div style={{maxWidth:'900px',margin:'0 auto',padding:'0 1.5rem 0.5rem',width:'100%'}}>
          <div style={{background:'#fee',border:'1px solid #fcc',color:'#c00',padding:'0.75rem',borderRadius:'0.5rem',fontSize:'0.875rem'}}>
            {error}
          </div>
        </div>
      )}

      {/* File Preview */}
      {uploadedFile && (
        <div style={{maxWidth:'900px',margin:'0 auto',padding:'0 1.5rem 0.5rem',width:'100%'}}>
          <div style={{background:'#e0f2fe',border:'1px solid #0284c7',padding:'1rem',borderRadius:'0.5rem',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
            <div style={{display:'flex',alignItems:'center',gap:'0.75rem',flex:1}}>
              <span style={{fontSize:'1.5rem'}}>📎</span>
              <div style={{flex:1}}>
                <p style={{fontSize:'0.875rem',fontWeight:'600',color:'#0c4a6e'}}>{uploadedFile.filename}</p>
                <input 
                  type="text" 
                  value={fileComment}
                  onChange={(e) => setFileComment(e.target.value)}
                  placeholder="Add a comment (optional)..."
                  style={{
                    width:'100%',
                    marginTop:'0.5rem',
                    padding:'0.5rem',
                    border:'1px solid #0284c7',
                    borderRadius:'0.25rem',
                    fontSize:'0.875rem'
                  }}
                />
              </div>
            </div>
            <button 
              onClick={cancelFileUpload}
              style={{
                background:'none',
                border:'none',
                cursor:'pointer',
                padding:'0.25rem',
                color:'#0c4a6e'
              }}
            >
              <X style={{width:'1.25rem',height:'1.25rem'}} />
            </button>
          </div>
        </div>
      )}

      {/* Input */}
      <div style={{background:'white',padding:'1rem 1.5rem',borderTop:'1px solid #e5e7eb'}}>
        <div style={{maxWidth:'900px',margin:'0 auto'}}>
          <div style={{fontSize:'0.75rem',color:'#6b7280',marginBottom:'0.5rem',textAlign:'center'}}>
            Try: 'give a task' • 'show tasks' • 'send feedback'
          </div>
          <form onSubmit={handleSendMessage} style={{display:'flex',gap:'0.75rem'}}>
            <input 
              type="file" 
              ref={fileInputRef}
              onChange={handleFileSelect}
              style={{display:'none'}}
            />
            <button 
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || loading}
              style={{
                background:'#f3f4f6',
                border:'1px solid #d1d5db',
                padding:'0.75rem',
                borderRadius:'0.5rem',
                cursor:uploading || loading?'not-allowed':'pointer',
                opacity:uploading || loading?0.5:1
              }}
            >
              <Paperclip style={{width:'1.25rem',height:'1.25rem',color:'#6b7280'}} />
            </button>
            <input 
              type="text" 
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder={uploadedFile ? "Press Send to upload file..." : "Type your message..."}
              disabled={loading || uploading}
              style={{
                flex:1,
                padding:'0.75rem 1rem',
                border:'1px solid #d1d5db',
                borderRadius:'0.5rem',
                fontSize:'1rem',
                outline:'none'
              }}
            />
            <button 
              type="submit" 
              disabled={loading || uploading || (!inputMessage.trim() && !uploadedFile)}
              style={{
                background:'linear-gradient(135deg, #1a1a1a 0%, #333 100%)',
                color:'white',
                padding:'0.75rem 1.5rem',
                borderRadius:'0.5rem',
                border:'none',
                cursor:loading || uploading || (!inputMessage.trim() && !uploadedFile)?'not-allowed':'pointer',
                display:'flex',
                alignItems:'center',
                gap:'0.5rem',
                fontWeight:'600',
                opacity:loading || uploading || (!inputMessage.trim() && !uploadedFile)?0.5:1
              }}
            >
              <Send style={{width:'1.25rem',height:'1.25rem'}} />
              Send
            </button>
          </form>
        </div>
      </div>
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};

export default App;
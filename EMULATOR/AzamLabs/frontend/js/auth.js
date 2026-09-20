/**
 * AzamLabs Client-Side Authentication Manager
 * Handles bearer token lifecycle, session persistence, and navigation guards.
 */

class AzamAuthManager {
  constructor() {
    this.tokenKey = 'azamlabs_session_token';
    this.userKey = 'azamlabs_session_user';
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  getUser() {
    return localStorage.getItem(this.userKey) || 'azam';
  }

  setSession(token, username) {
    localStorage.setItem(this.tokenKey, token);
    localStorage.setItem(this.userKey, username);
  }

  clearSession() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }

  async login(username, password, rememberMe = true) {
    try {
      const resp = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password: password,
          remember_me: rememberMe
        })
      });

      if (!resp.ok) {
        return false;
      }

      const data = await resp.json();
      if (data.token) {
        this.setSession(data.token, data.user);
        window.location.href = '/';
        return true;
      }
      return false;
    } catch (e) {
      console.error('Login error:', e);
      return false;
    }
  }

  async logout() {
    const token = this.getToken();
    try {
      if (token) {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }
    } catch (e) {
      console.warn('Logout notification error:', e);
    } finally {
      this.clearSession();
      window.location.href = '/login.html';
    }
  }

  async checkAuth(redirectOnFail = true) {
    const token = this.getToken();
    if (!token) {
      if (redirectOnFail) {
        window.location.href = '/login.html';
      }
      return false;
    }

    try {
      const resp = await fetch('/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (resp.ok) {
        return true;
      } else {
        this.clearSession();
        if (redirectOnFail) {
          window.location.href = '/login.html';
        }
        return false;
      }
    } catch (e) {
      // If offline or network glitch, honor local token
      return true;
    }
  }

  // Helper to inject Authorization header into outgoing API requests
  getAuthHeaders(baseHeaders = {}) {
    const token = this.getToken();
    const headers = { ...baseHeaders };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }
}

// Global Auth Instance
window.AzamAuth = new AzamAuthManager();

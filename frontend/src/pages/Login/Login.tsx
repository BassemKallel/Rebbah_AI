import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../providers/AuthProvider';
import './Login.css';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/', { replace: true });
    } catch (err: any) {
      const msg = err?.response?.data?.error || 'Identifiants invalides. Veuillez réessayer.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* ── Left Panel (Brand) ── */}
      <div className="login-left">
        <div className="login-left-content">
          <div className="login-brand">
            <span className="login-brand-icon">🤖</span>
            <span className="login-brand-name">TikTak AI</span>
          </div>

          <h1 className="login-headline">
            L'assistant IA intelligent<br />pour votre boutique
          </h1>
          <p className="login-subtext">
            Avec TikTak AI, automatisez vos conversations clients,
            gérez vos commandes et boostez vos ventes — le tout piloté par l'intelligence artificielle.
          </p>
        </div>

        <div className="login-left-footer">
          <p>© 2026 TikTak AI. Tous droits réservés.</p>
        </div>
      </div>

      {/* ── Right Panel (Form) ── */}
      <div className="login-right">
        <div className="login-form-wrapper">
          <h2 className="login-title">Connexion</h2>
          <p className="login-subtitle">Connectez-vous à votre compte pour continuer</p>

          <form onSubmit={handleSubmit} className="login-form">
            {error && <div className="login-error">{error}</div>}

            <div className="login-field">
              <label htmlFor="username">Nom d'utilisateur</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                autoComplete="username"
                required
                autoFocus
              />
            </div>

            <div className="login-field">
              <label htmlFor="password">Mot de passe</label>
              <div className="login-password-wrapper">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••••"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="login-eye-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                >
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            <button type="submit" className="login-btn" disabled={loading}>
              {loading ? (
                <span className="login-spinner" />
              ) : (
                'Se connecter'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

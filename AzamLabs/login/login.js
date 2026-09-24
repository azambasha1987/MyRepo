/* ============================================================================
   Azam Basha & PNetLab Enterprise Login Controller
   Handles authentication, session establishment, and error diagnostics.
   ============================================================================ */
(function () {
	'use strict';

	var form = document.getElementById('login-form');
	var userEl = document.getElementById('username');
	var passEl = document.getElementById('password');
	var consolePrefEl = document.getElementById('console-pref');
	var alertEl = document.getElementById('alert');
	var submitEl = document.getElementById('submit');
	var versionValueEl = document.getElementById('version-value');

	/* Resolve where to land after a successful login. */
	function redirectTarget() {
		var link = '';
		try {
			link = new URLSearchParams(window.location.search).get('link') || '';
		} catch (e) { link = ''; }
		if (!link) return '/main/';
		try {
			var u = new URL(link, window.location.origin);
			if (u.origin === window.location.origin) return u.pathname + u.search + u.hash;
		} catch (e) { /* fall through */ }
		return '/main/';
	}

	function showError(msg) {
		alertEl.textContent = msg || 'Sign in failed. Please try again.';
		alertEl.hidden = false;
	}
	function clearError() {
		alertEl.hidden = true;
		alertEl.textContent = '';
	}

	function setBusy(on) {
		submitEl.disabled = on;
		submitEl.classList.toggle('is-busy', on);
	}

	function submit(e) {
		if (e) e.preventDefault();
		clearError();
		var username = (userEl.value || '').trim();
		var password = passEl.value || '';
		if (!username || !password) {
			showError('Enter your username and password.');
			return;
		}
		setBusy(true);
		var consolePref = consolePrefEl ? consolePrefEl.value : 'native';
		var html5 = (consolePref === 'html5') ? 1 : 0;
		fetch('/api/auth', {
			method: 'POST',
			credentials: 'same-origin',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ username: username, password: password, html5: html5 })
		}).then(function (r) {
			return r.text().then(function (txt) {
				var body = {};
				try { body = txt ? JSON.parse(txt) : {}; } catch (err) { body = {}; }
				return { status: r.status, body: body };
			});
		}).then(function (res) {
			if (res.status === 200 && res.body && res.body.status === 'success') {
				window.location.replace(redirectTarget());
				return;
			}
			setBusy(false);
			if (res.status === 502 || res.status === 503) {
				showError('Backend service is reloading or temporarily busy (HTTP ' + res.status + '). Please try again in 5 seconds.');
			} else if (res.status === 429) {
				showError((res.body && res.body.message) || 'Too many failed login attempts. Please wait a moment.');
			} else if (res.status === 401) {
				showError('Invalid username or password.');
			} else {
				showError((res.body && res.body.message) || 'Invalid credentials.');
			}
			passEl.value = '';
			passEl.focus();
		}).catch(function () {
			setBusy(false);
			showError('Cannot reach the server. Check network connection or server status.');
		});
	}

	form.addEventListener('submit', submit);

	/* Logo fallback */
	var logoEl = document.getElementById('brand-logo');
	var markEl = document.getElementById('brand-mark');
	if (logoEl && markEl) {
		logoEl.addEventListener('error', function () {
			logoEl.hidden = true;
			markEl.hidden = false;
		});
	}

	if (window.PnqBranding) {
		window.PnqBranding.load().then(function (cfg) {
			window.PnqBranding.apply(cfg);
			document.title = (cfg.name || 'Azam Basha') + ' – Sign in';
			var hdr = document.getElementById('login-header');
			if (hdr && cfg.login_header) {
				hdr.textContent = cfg.login_header;
				hdr.hidden = false;
			}
			if (cfg.hide_default_creds) {
				var da = document.getElementById('default-account');
				if (da) da.hidden = true;
			}
		});
	}

	if (versionValueEl) {
		fetch('/login/version.php', { credentials: 'same-origin' })
			.then(function (r) { return r.json(); })
			.then(function (data) {
				versionValueEl.textContent = (data && data.version) ? data.version : 'v6.8.83';
			})
			.catch(function () {
				versionValueEl.textContent = 'v6.8.83';
			});
	}
})();

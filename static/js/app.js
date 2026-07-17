/** TemberaGo — form submissions & UI helpers */

// ---------------------------------------------------------------------------
// Toast notifications
// ---------------------------------------------------------------------------

function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// ---------------------------------------------------------------------------
// Generic form submission
// ---------------------------------------------------------------------------

async function submitForm(endpoint, payload, form, submitBtn, successLabel) {
  const originalHtml = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Sending…';

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok || !data.ok) {
      throw new Error(data.error || 'Something went wrong. Please try again.');
    }

    submitBtn.textContent = successLabel;
    submitBtn.style.background = '#25a244';
    showToast(data.message, 'success');
    form.reset();
    return data;
  } catch (err) {
    showToast(err.message, 'error');
    submitBtn.textContent = 'Try Again';
    throw err;
  } finally {
    setTimeout(() => {
      submitBtn.innerHTML = originalHtml;
      submitBtn.style.background = '';
      submitBtn.disabled = false;
    }, 4000);
  }
}

// ---------------------------------------------------------------------------
// Form handlers
// ---------------------------------------------------------------------------

function handleBooking(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');

  const payload = {
    full_name:   form.querySelector('#f-name')?.value,
    phone:       form.querySelector('#f-phone')?.value,
    email:       form.querySelector('#f-email')?.value,
    country:     form.querySelector('#f-country')?.value,
    service:     form.querySelector('#f-service')?.value,
    vehicle:     form.querySelector('#f-vehicle')?.value || '',
    pickup:      form.querySelector('#f-from')?.value,
    destination: form.querySelector('#f-to')?.value,
    travel_date: form.querySelector('#f-date')?.value,
    guests:      form.querySelector('#f-guests')?.value,
    notes:       form.querySelector('#f-notes')?.value,
  };

  submitForm('/api/booking', payload, form, btn, '✓ Request Sent!');
}

function handleContact(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');

  const payload = {
    name:    form.querySelector('#c-name')?.value,
    email:   form.querySelector('#c-email')?.value,
    subject: form.querySelector('#c-subject')?.value,
    message: form.querySelector('#c-message')?.value,
  };

  submitForm('/api/contact', payload, form, btn, '✓ Message Sent!');
}

function handleQuickQuote(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');

  const payload = {
    service:     form.querySelector('#qs-service')?.value,
    origin:      form.querySelector('#qs-from')?.value,
    destination: form.querySelector('#qs-to')?.value,
    travel_date: form.querySelector('#qs-date')?.value,
  };

  submitForm('/api/quick-quote', payload, form, btn, '✓ Quote Requested!')
    .then(() => {
      prefillBookingForm(payload);
      document.getElementById('booking')?.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(() => {});
}

// ---------------------------------------------------------------------------
// Booking form prefill (from quick-quote)
// ---------------------------------------------------------------------------

function prefillBookingForm({ service, origin, destination, travel_date }) {
  const map = {
    '#f-service': service,
    '#f-from':    origin,
    '#f-to':      destination,
    '#f-date':    travel_date,
  };
  Object.entries(map).forEach(([sel, val]) => {
    const el = document.querySelector(sel);
    if (el && val) el.value = val;
  });
}

// ---------------------------------------------------------------------------
// Navigation helpers
// ---------------------------------------------------------------------------

function scrollToBooking() {
  document.getElementById('booking')?.scrollIntoView({ behavior: 'smooth' });
}

function toggleMenu() {
  const menu = document.getElementById('mobileMenu');
  menu.classList.toggle('open');
  document.body.style.overflow = menu.classList.contains('open') ? 'hidden' : '';
}

function filterFleet(cat, btn) {
  document.querySelectorAll('.fleet-tab').forEach((t) => t.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.fleet-card').forEach((card) => {
    const match = cat === 'all' || card.dataset.cat === cat;
    card.style.display = match ? '' : 'none';
  });
}

// ---------------------------------------------------------------------------
// DOMContentLoaded — observers & init
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  // Sticky navbar
  const navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener(
      'scroll',
      () => navbar.classList.toggle('scrolled', window.scrollY > 60),
      { passive: true }
    );
  }

  // Restrict date inputs to today or later
  const today = new Date().toISOString().split('T')[0];
  document.querySelectorAll('input[type="date"]').forEach((input) => {
    input.min = today;
  });

  // Scroll-reveal animation
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );
  document.querySelectorAll('.reveal').forEach((el) => revealObserver.observe(el));

  // Animated stat counters
  function animateCounters() {
    document.querySelectorAll('.stat-num').forEach((el) => {
      const text = el.textContent;
      const num = parseFloat(text);
      if (isNaN(num)) return;
      const suffix = text.replace(/[\d.]/g, '');
      let start = 0;
      const duration = 1800;
      const step = (timestamp) => {
        if (!start) start = timestamp;
        const progress = Math.min((timestamp - start) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(num * ease) + suffix;
        if (progress < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  const statsBar = document.querySelector('.stats-bar');
  if (statsBar) {
    const statsObserver = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          animateCounters();
          statsObserver.disconnect();
        }
      },
      { threshold: 0.5 }
    );
    statsObserver.observe(statsBar);
  }

  // Respect reduced-motion preference
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.reveal').forEach((el) => {
      el.classList.add('visible');
      el.style.transition = 'none';
    });
  }
});

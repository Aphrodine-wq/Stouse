// VibeHouse — Interaction layer
// Keeps things feeling native: scroll-aware nav, stagger reveals,
// touch-friendly interactions.

(function () {
  'use strict';

  // ---- Scroll-aware navbar ----
  const nav = document.querySelector('.ios-nav');
  if (nav) {
    let lastY = 0;
    let ticking = false;

    function onScroll() {
      const y = window.scrollY;
      if (y > 10) {
        nav.style.background = 'rgba(255,255,255,0.92)';
      } else {
        nav.style.background = 'rgba(255,255,255,0.72)';
      }
      lastY = y;
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) {
        requestAnimationFrame(onScroll);
        ticking = true;
      }
    }, { passive: true });
  }

  // ---- Intersection Observer for stagger animations ----
  const staggerEls = document.querySelectorAll('[data-stagger]');
  if (staggerEls.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('stagger-children');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    staggerEls.forEach(function (el) { observer.observe(el); });
  }

  // ---- Fade-in on scroll ----
  const revealEls = document.querySelectorAll('[data-reveal]');
  if (revealEls.length && 'IntersectionObserver' in window) {
    revealEls.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity 0.5s cubic-bezier(0.25,0.46,0.45,0.94), transform 0.5s cubic-bezier(0.25,0.46,0.45,0.94)';
    });

    const revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var delay = entry.target.getAttribute('data-reveal') || '0';
          setTimeout(function () {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
          }, parseInt(delay, 10));
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    revealEls.forEach(function (el) { revealObserver.observe(el); });
  }

  // ---- Animated counters on stat cards ----
  function animateCount(el, target, duration) {
    var start = 0;
    var startTime = null;
    var prefix = el.getAttribute('data-prefix') || '';
    var suffix = el.getAttribute('data-suffix') || '';

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      // Ease out cubic
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = Math.floor(eased * target);
      el.textContent = prefix + current.toLocaleString() + suffix;
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }

    requestAnimationFrame(step);
  }

  var countEls = document.querySelectorAll('[data-count]');
  if (countEls.length && 'IntersectionObserver' in window) {
    var countObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var target = parseInt(entry.target.getAttribute('data-count'), 10);
          animateCount(entry.target, target, 1200);
          countObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    countEls.forEach(function (el) { countObserver.observe(el); });
  }

  // ---- Progress bar animation ----
  var progressBars = document.querySelectorAll('.ios-progress-fill[data-width]');
  if (progressBars.length && 'IntersectionObserver' in window) {
    var progressObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var w = entry.target.getAttribute('data-width');
          entry.target.style.width = w;
          progressObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    progressBars.forEach(function (el) {
      el.style.width = '0';
      progressObserver.observe(el);
    });
  }

  // ---- Touch feedback on interactive cards ----
  var cards = document.querySelectorAll('.feature-card, .project-card, .step-item');
  cards.forEach(function (card) {
    card.addEventListener('touchstart', function () {
      card.style.transform = 'scale(0.98)';
    }, { passive: true });

    card.addEventListener('touchend', function () {
      card.style.transform = '';
    }, { passive: true });
  });

  // ---- Mobile tab bar active state ----
  var currentPath = window.location.pathname;
  var tabItems = document.querySelectorAll('.tab-item');
  tabItems.forEach(function (tab) {
    var href = tab.getAttribute('href');
    if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
      tab.classList.add('active');
    }
  });

})();

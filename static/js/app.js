/**
 * 21 Void Technologies - Core Application Controller
 * Strict rules:
 * - jQuery $.ajax is the ONLY AJAX mechanism.
 * - SweetAlert2 is the ONLY notification and dialog system.
 * - Zero keyboard shortcuts / hotkeys anywhere. Pure mouse & touch interaction.
 * - Reusable modal system for Add, Edit, Detail across all entities.
 * - Uniform JSON contract handling: {title, message, icon, data, pagination, errors}.
 */

// Helper to retrieve CSRF token dynamically from meta tag, form input, or cookie
function getCsrfToken() {
  const metaToken = $('meta[name="csrf-token"]').attr('content');
  if (metaToken) return metaToken;
  
  const formToken = $('input[name="csrfmiddlewaretoken"]').val();
  if (formToken) return formToken;

  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, 10) === 'csrftoken=') {
        cookieValue = decodeURIComponent(cookie.substring(10));
        break;
      }
    }
  }
  return cookieValue;
}

// Global jQuery AJAX Setup with dynamic token injection
$.ajaxSetup({
  beforeSend: function (xhr, settings) {
    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader('X-CSRFToken', getCsrfToken());
    }
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
  }
});

// Centralized SweetAlert2 helper (Safe resolution of window.Swal)
function notifySwal(title, message, icon, timer = 2500) {
  const swalInstance = window.Swal || window.Sweetalert2;
  if (!swalInstance) {
    console.log('[Notice]', title, message);
    return Promise.resolve();
  }
  return swalInstance.fire({
    title: title || 'Notice',
    text: message || '',
    icon: icon || 'info',
    timer: timer,
    timerProgressBar: timer ? true : false,
    showConfirmButton: timer ? false : true,
    confirmButtonColor: '#0f172a',
    background: '#ffffff',
    color: '#0f172a',
    customClass: {
      container: 'swal-high-z',
      popup: 'rounded-[24px] shadow-2xl border border-slate-100'
    }
  });
}

// Centralized confirmation dialog
function confirmSwal(title, text, confirmButtonText = 'Yes, proceed', onConfirm = null) {
  const swalInstance = window.Swal || window.Sweetalert2;
  if (!swalInstance) {
    if (typeof onConfirm === 'function') {
      onConfirm({ isConfirmed: true });
    }
    return Promise.resolve({ isConfirmed: true });
  }
  const promise = swalInstance.fire({
    title: title || 'Are you sure?',
    text: text || "This action cannot be undone.",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#0f172a',
    cancelButtonColor: '#94a3b8',
    confirmButtonText: confirmButtonText,
    cancelButtonText: 'Cancel',
    reverseButtons: true,
    background: '#ffffff',
    color: '#0f172a',
    customClass: {
      container: 'swal-high-z',
      popup: 'rounded-[24px] shadow-2xl border border-slate-100'
    }
  });

  if (typeof onConfirm === 'function') {
    return promise.then((result) => {
      if (result.isConfirmed) {
        onConfirm(result);
      }
      return result;
    });
  }

  return promise;
}

// Global window helpers for compatibility across all templates
window.notifySwal = notifySwal;
window.confirmSwal = confirmSwal;
window.showNotification = function (message, icon = 'info', title = null) {
  return notifySwal(title || (icon === 'error' ? 'Error' : (icon === 'success' ? 'Success' : 'Notice')), message, icon);
};
window.closeModal = function () {
  ModalManager.close();
};
window.paginateTable = function (containerSelector, pageNumber) {
  refreshTable(containerSelector, { page: pageNumber });
};

// Global Number & Currency Formatting Helpers (Localisation)
window.formatMoney = function (amount, symbol) {
  const sym = symbol !== undefined ? symbol : (window.APP_CURRENCY_SYMBOL || '$');
  if (amount === null || amount === undefined || amount === '') {
    return sym + '0.00';
  }
  const cleaned = String(amount).replace(/[^0-9.-]/g, '');
  const num = parseFloat(cleaned);
  if (isNaN(num)) return sym + '0.00';
  return sym + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

window.formatNumber = function (val, decimals = 0) {
  if (val === null || val === undefined || val === '') {
    return '0';
  }
  const cleaned = String(val).replace(/[^0-9.-]/g, '');
  const num = parseFloat(cleaned);
  if (isNaN(num)) return '0';
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
};

// Reusable Modal Shell Controller
const ModalManager = {
  shell: null,
  container: null,
  
  init() {
    this.shell = $('#app-modal-shell');
    this.container = $('#modal-content-container');
    
    // Close triggers
    $(document).off('click', '[data-modal-close]').on('click', '[data-modal-close]', () => this.close());
    $(document).off('click', '#app-modal-shell').on('click', '#app-modal-shell', (e) => {
      if ($(e.target).is('#app-modal-shell')) {
        this.close();
      }
    });
    
    // Open triggers: Any element with data-modal-url
    $(document).off('click', '[data-modal-url]').on('click', '[data-modal-url]', function (e) {
      e.preventDefault();
      const url = $(this).attr('data-modal-url');
      const size = $(this).attr('data-modal-size') || 'max-w-2xl';
      ModalManager.open(url, size);
    });
  },
  
  open(url, sizeClass = 'max-w-2xl') {
    this.shell = $('#app-modal-shell');
    this.container = $('#modal-content-container');
    if (!this.shell.length) return;
    
    // Reset container size class
    const dialog = this.shell.find('.modal-dialog');
    dialog.removeClass('max-w-xs max-w-sm max-w-md max-w-lg max-w-xl max-w-2xl max-w-3xl max-w-4xl max-w-5xl max-w-6xl max-w-7xl max-w-full').addClass(sizeClass);
    
    // Show skeleton loader in modal
    this.container.html(`
      <div class="p-6 space-y-4">
        <div class="h-6 w-1/3 skeleton rounded"></div>
        <div class="h-4 w-1/2 skeleton rounded"></div>
        <div class="h-10 w-full skeleton rounded mt-4"></div>
        <div class="h-10 w-full skeleton rounded"></div>
        <div class="h-10 w-full skeleton rounded"></div>
        <div class="flex justify-end space-x-3 pt-4">
          <div class="h-9 w-20 skeleton rounded"></div>
          <div class="h-9 w-28 skeleton rounded"></div>
        </div>
      </div>
    `);
    
    this.shell.removeClass('hidden').addClass('flex');
    setTimeout(() => this.shell.addClass('modal-active'), 10);
    
    // Fetch modal HTML via jQuery $.ajax
    $.ajax({
      url: url,
      type: 'GET',
      cache: false,
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      success: (html) => {
        this.container.html(html);
      },
      error: (xhr) => {
        const res = xhr.responseJSON || {};
        notifySwal(res.title || 'Error', res.message || 'Failed to load content', res.icon || 'error');
        this.close();
      }
    });
  },
  
  close() {
    if (!this.shell || !this.shell.length) return;
    this.shell.removeClass('modal-active');
    setTimeout(() => {
      this.shell.removeClass('flex').addClass('hidden');
      this.container.empty();
    }, 200);
  }
};

// Form and Input Validation Error Handler
function clearFormErrors($form) {
  $form.find('.input-error').removeClass('input-error');
  $form.find('.field-error-text').remove();
}

function applyFormErrors($form, errors) {
  clearFormErrors($form);
  if (!errors || typeof errors !== 'object') return;
  
  let firstKey = null;
  for (const [field, message] of Object.entries(errors)) {
    if (!firstKey) firstKey = field;
    const $input = $form.find(`[name="${field}"]`);
    if ($input.length) {
      $input.addClass('input-error');
      $input.after(`<div class="field-error-text">${message}</div>`);
    }
  }
  
  if (firstKey) {
    $form.find(`[name="${firstKey}"]`).focus();
  }
}

// Global AJAX Form Handler
function initAjaxForms() {
  $(document).off('submit', 'form[data-ajax="true"]').on('submit', 'form[data-ajax="true"]', function (e) {
    e.preventDefault();
    e.stopPropagation();
    
    const $form = $(this);
    const $submitBtn = $form.find('button[type="submit"]');
    const refreshTableSelector = $form.attr('data-refresh-table');
    const redirectUrl = $form.attr('data-redirect');
    const isModal = $form.closest('#app-modal-shell').length > 0;
    const preventDefaultSwal = $form.attr('data-prevent-default-swal') === 'true';
    
    clearFormErrors($form);
    $submitBtn.addClass('btn-loading').prop('disabled', true);
    
    // Form target and method
    const actionUrl = $form.attr('action') || window.location.href;
    const method = ($form.attr('method') || 'POST').toUpperCase();

    // Serialize data (support file uploads via FormData if files or multipart)
    const hasFiles = $form.find('input[type="file"]').length > 0 || $form.attr('enctype') === 'multipart/form-data';
    let formData;
    let ajaxSettings = {
      url: actionUrl,
      type: method,
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest'
      }
    };

    if (hasFiles) {
      formData = new FormData($form[0]);
      ajaxSettings.data = formData;
      ajaxSettings.processData = false;
      ajaxSettings.contentType = false;
    } else {
      formData = $form.serialize();
      ajaxSettings.data = formData;
    }

    $.ajax($.extend(ajaxSettings, {


      success: function (res) {
        $submitBtn.removeClass('btn-loading').prop('disabled', false);
        
        const isLogin = $form.attr('id') === 'login-form' || (typeof actionUrl === 'string' && actionUrl.indexOf('/accounts/login') !== -1);

        // SweetAlert2 notification according to uniform envelope (bypassed on login success)
        if (!preventDefaultSwal && !isLogin) {
          notifySwal(res.title || 'Success', res.message || 'Operation successful', res.icon || 'success', 2200);
        }
        
        // Modal handling
        if (isModal) {
          ModalManager.close();
        }

        // Direct instant redirect for login without modal or artificial delay
        if (isLogin) {
          const dest = (res.data && res.data.redirect_url) ? res.data.redirect_url : (redirectUrl || '/');
          window.location.href = dest;
          return;
        }
        
        // Table refresh
        if (refreshTableSelector && $(refreshTableSelector).length) {
          refreshTable(refreshTableSelector);
        } else if (isModal && window.location.pathname === '/') {
          // If modal submitted on dashboard, reload after short pause to show updated counts
          setTimeout(() => { window.location.reload(); }, 1200);
        }
        
        // Custom callback or redirect
        if (res.data && res.data.redirect_url) {
          setTimeout(() => { window.location.href = res.data.redirect_url; }, 800);
        } else if (redirectUrl) {
          setTimeout(() => { window.location.href = redirectUrl; }, 800);
        }
        
        // Trigger optional custom event
        $(document).trigger('ajax-form-success', [res, $form]);
      },
      error: function (xhr) {
        $submitBtn.removeClass('btn-loading').prop('disabled', false);
        const res = xhr.responseJSON || {};
        
        if (res.errors) {
          applyFormErrors($form, res.errors);
        }
        
        notifySwal(
          res.title || 'Validation Error',
          res.message || 'Please review the highlighted errors.',
          res.icon || 'error',
          3500
        );
      }
    }));
  });
}

// Global Delete Action Handler (Supports [data-delete-url], [data-action-url], and .btn-delete-confirm)
function initDeleteActions() {
  $(document).off('click', '[data-delete-url], [data-action-url], .btn-delete-confirm').on('click', '[data-delete-url], [data-action-url], .btn-delete-confirm', function (e) {
    e.preventDefault();
    const $btn = $(this);
    const deleteUrl = $btn.attr('data-delete-url') || $btn.attr('data-action-url');
    if (!deleteUrl) return;

    const itemTitle = $btn.attr('data-item-title') || 'this item';
    const confirmTitle = $btn.attr('data-confirm-title') || 'Delete Confirmation';
    const confirmMsg = $btn.attr('data-confirm-message') || `Are you sure you want to permanently delete "${itemTitle}"?`;
    const refreshTableSelector = $btn.attr('data-refresh-table') || $btn.attr('data-refresh-target');
    const $row = $btn.closest('tr');
    
    confirmSwal(confirmTitle, confirmMsg).then((result) => {
      if (result.isConfirmed) {
        if ($row.length) {
          $row.css('opacity', '0.4');
        }
        
        $.ajax({
          url: deleteUrl,
          type: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
          },
          success: function (res) {
            notifySwal(res.title || 'Deleted', res.message || 'Item deleted successfully', res.icon || 'success', 2000);
            
            if ($row.length) {
              $row.fadeOut(250, function () {
                $(this).remove();
                if (refreshTableSelector && $(refreshTableSelector).length) {
                  refreshTable(refreshTableSelector);
                }
              });
            } else if (refreshTableSelector && $(refreshTableSelector).length) {
              refreshTable(refreshTableSelector);
            }
          },
          error: function (xhr) {
            if ($row.length) {
              $row.css('opacity', '1');
            }
            const res = xhr.responseJSON || {};
            notifySwal(res.title || 'Error', res.message || 'Could not delete item', res.icon || 'error', 3500);
          }
        });
      }
    });
  });
}

/**
 * Universal Searchable Combobox with Keyboard Arrow Navigation
 * Supports ArrowDown, ArrowUp, Enter, Escape, Live Typing Filter, and Click-away.
 */
window.initSearchableCombobox = function (wrapperSelector) {
  const $wrappers = $(wrapperSelector || '.custom-searchable-combobox');
  if (!$wrappers.length) return;

  $wrappers.each(function () {
    const $wrap = $(this);
    if ($wrap.data('combobox-active')) return;
    $wrap.data('combobox-active', true);

    const $input = $wrap.find('.combobox-input');
    const $hidden = $wrap.find('.combobox-hidden');
    const $dropdown = $wrap.find('.combobox-dropdown');
    let activeIdx = -1;

    function doFilter(query) {
      const q = (query || '').toLowerCase().trim();
      let matches = 0;
      const $options = $dropdown.find('.combobox-option');
      activeIdx = -1;
      $options.removeClass('bg-blue-100 ring-1 ring-blue-500 font-bold');

      $options.each(function () {
        const text = $(this).text().toLowerCase();
        const searchAttr = $(this).attr('data-search') ? $(this).attr('data-search').toLowerCase() : text;
        if (!q || searchAttr.includes(q)) {
          $(this).removeClass('hidden');
          matches++;
        } else {
          $(this).addClass('hidden');
        }
      });

      if (matches === 0) {
        if (!$dropdown.find('.combobox-empty-msg').length) {
          $dropdown.append('<div class="p-3 text-center text-xs text-slate-400 italic combobox-empty-msg">No matching options found</div>');
        } else {
          $dropdown.find('.combobox-empty-msg').removeClass('hidden');
        }
      } else {
        $dropdown.find('.combobox-empty-msg').addClass('hidden');
      }
      $dropdown.removeClass('hidden');
    }

    function updateHighlight() {
      const $vis = $dropdown.find('.combobox-option:not(.hidden)');
      $vis.removeClass('bg-blue-100 ring-1 ring-blue-500 font-bold');
      if (activeIdx >= 0 && activeIdx < $vis.length) {
        const $target = $vis.eq(activeIdx);
        $target.addClass('bg-blue-100 ring-1 ring-blue-500 font-bold');
        if ($target[0] && $target[0].scrollIntoView) {
          $target[0].scrollIntoView({ block: 'nearest' });
        }
      }
    }

    $input.off('focus input').on('focus input', function () {
      doFilter($(this).val());
    });

    $input.off('keydown').on('keydown', function (e) {
      const $vis = $dropdown.find('.combobox-option:not(.hidden)');
      if ($dropdown.hasClass('hidden')) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          doFilter($(this).val());
          return;
        }
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIdx++;
        if (activeIdx >= $vis.length) activeIdx = 0;
        updateHighlight();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIdx--;
        if (activeIdx < 0) activeIdx = $vis.length - 1;
        updateHighlight();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (activeIdx >= 0 && activeIdx < $vis.length) {
          $vis.eq(activeIdx).trigger('click');
        } else if ($vis.length > 0) {
          $vis.first().trigger('click');
        }
      } else if (e.key === 'Escape') {
        $dropdown.addClass('hidden');
      }
    });

    $dropdown.off('click', '.combobox-option').on('click', '.combobox-option', function () {
      const id = $(this).attr('data-id');
      const name = $(this).attr('data-name') || $(this).text().trim();
      const dataset = $(this).data();
      $hidden.val(id).trigger('change');
      $input.val(name).trigger('change');
      $dropdown.addClass('hidden');
      $wrap.trigger('combobox:selected', [id, name, dataset]);
    });

    $(document).on('click', function (e) {
      if (!$(e.target).closest($wrap).length) {
        $dropdown.addClass('hidden');
      }
    });
  });
};

// Table AJAX Refresh Helper
function refreshTable(containerSelector, customParams = {}) {
window.refreshTable = refreshTable;
  const $container = $(containerSelector);
  if (!$container.length) return;
  
  const url = $container.attr('data-table-url');
  if (!url) return;
  
  // Show table skeleton opacity
  $container.find('tbody').addClass('opacity-50 pointer-events-none');
  
  // Collect search & filter params from associated filter form if present
  const filterFormId = $container.attr('data-filter-form');
  let params = customParams;
  if (filterFormId && $(filterFormId).length) {
    const serialized = $(filterFormId).serializeArray();
    serialized.forEach(item => {
      params[item.name] = item.value;
    });
  }
  
  $.ajax({
    url: url,
    type: 'GET',
    cache: false,
    data: params,
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    success: function (html) {
      $container.html(html);
    },
    error: function () {
      $container.find('tbody').removeClass('opacity-50 pointer-events-none');
      notifySwal('Error', 'Failed to refresh table data', 'error');
    }
  });
}

// Sidebar Toggle Controller
function updateSidebarToggleIcon(isCollapsed) {
  const $icon = $('#sidebar-toggle-icon');
  const $btn = $('#sidebar-toggle-btn');
  if ($icon.length) {
    if (isCollapsed) {
      $icon.removeClass('fa-indent fa-outdent fa-chevron-left fa-bars fa-bars-staggered').addClass('fa-chevron-right');
      if ($btn.length) $btn.attr('title', 'Expand Sidebar');
    } else {
      $icon.removeClass('fa-indent fa-outdent fa-chevron-right fa-bars fa-bars-staggered').addClass('fa-chevron-left');
      if ($btn.length) $btn.attr('title', 'Collapse Sidebar');
    }
  }
}

function initSidebar() {
  const isCollapsed = localStorage.getItem('21void_sidebar_collapsed') === 'true';
  if (isCollapsed) {
    $('html').addClass('sidebar-is-collapsed');
    $('#app-sidebar').addClass('collapsed');
  } else {
    $('html').removeClass('sidebar-is-collapsed');
    $('#app-sidebar').removeClass('collapsed');
  }
  updateSidebarToggleIcon(isCollapsed);

  // Enable transitions after initial frame has painted
  setTimeout(() => {
    $('#app-sidebar').addClass('sidebar-ready');
  }, 50);

  function toggleSidebar(e) {
    if (e) e.preventDefault();
    const willCollapse = !$('#app-sidebar').hasClass('collapsed');
    if (willCollapse) {
      $('html').addClass('sidebar-is-collapsed');
      $('#app-sidebar').addClass('collapsed');
    } else {
      $('html').removeClass('sidebar-is-collapsed');
      $('#app-sidebar').removeClass('collapsed');
    }
    updateSidebarToggleIcon(willCollapse);
    localStorage.setItem('21void_sidebar_collapsed', willCollapse ? 'true' : 'false');
  }

  $(document).off('click', '#sidebar-toggle-btn, #topbar-sidebar-toggle-btn, .btn-toggle-sidebar')
    .on('click', '#sidebar-toggle-btn, #topbar-sidebar-toggle-btn, .btn-toggle-sidebar', toggleSidebar);

  // Clicking brand logo when sidebar is collapsed expands it
  $(document).off('click', '#sidebar-brand-logo')
    .on('click', '#sidebar-brand-logo', function (e) {
      if ($('#app-sidebar').hasClass('collapsed')) {
        toggleSidebar(e);
      }
    });
}


// Global Initialization
$(document).ready(function () {
  ModalManager.init();
  initAjaxForms();
  initDeleteActions();
  initSidebar();
  initFeatureSearch();
  console.log('21 Void Technologies Core JS initialized successfully.');
});

// ==========================================================================
// Sidebar Feature Filter & Search (Like in Clarity Retail LAN)
// ==========================================================================

function filterSidebarLinks() {
  const input = document.getElementById('sidebar-filter-input');
  if (!input) return;
  const rawQuery = (input.value || '').trim();
  const query = rawQuery.toLowerCase();
  const clearBtn = document.getElementById('sidebar-filter-clear');
  const emptyNotice = document.getElementById('sidebar-filter-empty');

  if (clearBtn) {
    if (rawQuery.length > 0) {
      clearBtn.classList.remove('hidden');
    } else {
      clearBtn.classList.add('hidden');
    }
  }

  const links = document.querySelectorAll('#app-sidebar nav .sidebar-link');
  const groups = document.querySelectorAll('#app-sidebar nav > div:not(#sidebar-filter-empty)');
  const posBtn = document.getElementById('sidebar-pos-terminal-btn');

  if (!query) {
    links.forEach(el => el.style.display = '');
    groups.forEach(g => g.style.display = '');
    if (posBtn) posBtn.style.display = '';
    if (emptyNotice) emptyNotice.classList.add('hidden');
    return;
  }

  let totalVisible = 0;

  // Filter links
  links.forEach(link => {
    const text = (link.textContent || '').toLowerCase();
    const title = (link.getAttribute('title') || '').toLowerCase();
    const keywords = (link.getAttribute('data-keywords') || '').toLowerCase();
    const matches = text.includes(query) || title.includes(query) || keywords.includes(query);
    link.style.display = matches ? 'flex' : 'none';
    if (matches) totalVisible++;
  });

  // Filter POS button
  if (posBtn) {
    const posText = (posBtn.textContent || '').toLowerCase();
    const posKeywords = 'pos point of sale checkout cashier till terminal instant checkout receipt register f2';
    const posMatches = posText.includes(query) || posKeywords.includes(query);
    posBtn.style.display = posMatches ? 'flex' : 'none';
    if (posMatches) totalVisible++;
  }

  // Filter group headers
  groups.forEach(group => {
    const visibleLinks = group.querySelectorAll('.sidebar-link:not([style*="display: none"])');
    group.style.display = visibleLinks.length > 0 ? '' : 'none';
  });

  if (emptyNotice) {
    if (totalVisible === 0) {
      emptyNotice.classList.remove('hidden');
    } else {
      emptyNotice.classList.add('hidden');
    }
  }
}
window.filterSidebarLinks = filterSidebarLinks;

function clearSidebarFilter() {
  const input = document.getElementById('sidebar-filter-input');
  if (input) {
    input.value = '';
    filterSidebarLinks();
    input.focus();
  }
}
window.clearSidebarFilter = clearSidebarFilter;

function handleCollapsedSearchClick() {
  openFeatureSearchModal();
}
window.handleCollapsedSearchClick = handleCollapsedSearchClick;

function openFeatureSearchModalFromSidebar() {
  const input = document.getElementById('sidebar-filter-input');
  const q = input ? input.value : '';
  openFeatureSearchModal(q);
}
window.openFeatureSearchModalFromSidebar = openFeatureSearchModalFromSidebar;

// ==========================================================================
// Global Feature Search Command Palette Modal (Apple Minimalist)
// ==========================================================================

let globalFeaturesCache = null;
let filteredSearchResults = [];
let activeFeatureSearchIndex = -1;
let currentFeatureCategory = 'ALL';
let featureSearchDebounce = null;
let isFeaturesLoading = false;

const FEATURE_CACHE_KEY = 'gadget_features_catalog';
const FEATURE_CACHE_TIME_KEY = 'gadget_features_catalog_time';
const FEATURE_CACHE_TTL = 3600000; // 1 hour

async function loadAllSystemFeatures() {
  if (globalFeaturesCache && globalFeaturesCache.length > 0) {
    return globalFeaturesCache;
  }

  try {
    const cached = localStorage.getItem(FEATURE_CACHE_KEY);
    const time = localStorage.getItem(FEATURE_CACHE_TIME_KEY);
    if (cached && time && (Date.now() - parseInt(time) < FEATURE_CACHE_TTL)) {
      globalFeaturesCache = JSON.parse(cached);
      updateTotalFeaturesCount(globalFeaturesCache.length);
      return globalFeaturesCache;
    }
  } catch (err) {}

  if (isFeaturesLoading) {
    return new Promise(resolve => {
      const check = setInterval(() => {
        if (!isFeaturesLoading && globalFeaturesCache) {
          clearInterval(check);
          resolve(globalFeaturesCache);
        }
      }, 80);
    });
  }

  isFeaturesLoading = true;
  try {
    const resp = await fetch('/api/search-features/');
    const data = await resp.json();
    if (data && data.features) {
      globalFeaturesCache = data.features;
      try {
        localStorage.setItem(FEATURE_CACHE_KEY, JSON.stringify(globalFeaturesCache));
        localStorage.setItem(FEATURE_CACHE_TIME_KEY, Date.now().toString());
      } catch (e) {}
      updateTotalFeaturesCount(globalFeaturesCache.length);
      isFeaturesLoading = false;
      return globalFeaturesCache;
    }
  } catch (err) {
    console.error('Failed to load system features:', err);
  }
  isFeaturesLoading = false;
  return [];
}

function updateTotalFeaturesCount(count) {
  const counter = document.getElementById('featuresTotalCounter');
  if (counter) counter.textContent = `${count} features indexed`;
}

function openFeatureSearchModal(initialQuery = '') {
  const modal = document.getElementById('featureSearchModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  modal.classList.add('flex');

  const input = document.getElementById('globalFeatureSearchInput');
  if (input) {
    input.value = initialQuery;
    setTimeout(() => {
      input.focus();
      input.select();
    }, 80);
  }

  currentFeatureCategory = 'ALL';
  updateCategoryChipButtons('ALL');
  activeFeatureSearchIndex = -1;

  loadAllSystemFeatures().then(() => {
    performFeatureSearch(initialQuery);
  });
}
window.openFeatureSearchModal = openFeatureSearchModal;

function closeFeatureSearchModal() {
  const modal = document.getElementById('featureSearchModal');
  if (!modal) return;
  modal.classList.add('hidden');
  modal.classList.remove('flex');
}
window.closeFeatureSearchModal = closeFeatureSearchModal;

function handleSearchOverlayClick(e) {
  if (e.target.id === 'featureSearchModal') {
    closeFeatureSearchModal();
  }
}
window.handleSearchOverlayClick = handleSearchOverlayClick;

function filterFeaturesByCategory(cat) {
  currentFeatureCategory = cat;
  updateCategoryChipButtons(cat);
  const input = document.getElementById('globalFeatureSearchInput');
  performFeatureSearch(input ? input.value : '');
}
window.filterFeaturesByCategory = filterFeaturesByCategory;

function updateCategoryChipButtons(cat) {
  document.querySelectorAll('#featureCategoryChips .search-cat-chip').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-cat') === cat);
  });
}

function performFeatureSearch(rawQuery) {
  const container = document.getElementById('featureSearchResults');
  if (!container) return;

  if (!globalFeaturesCache || globalFeaturesCache.length === 0) {
    container.innerHTML = `
      <div class="py-12 text-center text-slate-400 text-xs">
        <i class="fas fa-circle-notch fa-spin text-lg text-blue-600 mb-2"></i>
        <div>Loading system features...</div>
      </div>`;
    return;
  }

  const query = (rawQuery || '').trim().toLowerCase();
  let candidates = globalFeaturesCache;

  if (currentFeatureCategory !== 'ALL') {
    candidates = candidates.filter(f => f.category === currentFeatureCategory);
  }

  if (!query) {
    filteredSearchResults = candidates;
    activeFeatureSearchIndex = 0;
    renderFeatureSearchResults(filteredSearchResults, '');
    return;
  }

  const searchTerms = query.split(/\s+/).filter(Boolean);
  const scored = [];

  for (const f of candidates) {
    let score = 0;
    let matchCount = 0;
    const nameLower = (f.name || '').toLowerCase();
    const descLower = (f.description || '').toLowerCase();
    const keywords = (f.keywords || []).map(k => k.toLowerCase());
    const fullHaystack = [nameLower, descLower, ...keywords].join(' ');

    if (fullHaystack.includes(query)) score += 5;
    if (nameLower.startsWith(query)) score += 6;

    for (const term of searchTerms) {
      let termMatched = false;
      if (nameLower.includes(term)) {
        score += 4;
        termMatched = true;
      }
      if (keywords.some(k => k.includes(term))) {
        score += 3;
        termMatched = true;
      }
      if (descLower.includes(term)) {
        score += 1.5;
        termMatched = true;
      }
      if (termMatched) matchCount++;
    }

    if (matchCount > 0 || score > 0) {
      scored.push({ feature: f, score: score + matchCount * 2 });
    }
  }

  scored.sort((a, b) => b.score - a.score);
  filteredSearchResults = scored.map(s => s.feature);
  activeFeatureSearchIndex = filteredSearchResults.length > 0 ? 0 : -1;
  renderFeatureSearchResults(filteredSearchResults, query);
}

function highlightSearchMatch(text, query) {
  if (!text || !query) return text || '';
  const terms = query.split(/\s+/).filter(Boolean);
  if (terms.length === 0) return text;
  const pattern = new RegExp(`(${terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  return text.replace(pattern, '<mark>$1</mark>');
}

function renderFeatureSearchResults(results, query) {
  const container = document.getElementById('featureSearchResults');
  if (!container) return;

  if (!results || results.length === 0) {
    container.innerHTML = `
      <div class="py-12 text-center text-slate-400 text-xs">
        <i class="fas fa-search-minus text-2xl text-slate-300 mb-2"></i>
        <div class="font-semibold text-slate-700">No matching features found</div>
        <div class="text-[11px] text-slate-400 mt-0.5">Try searching with a different keyword or category</div>
      </div>`;
    return;
  }

  let html = '';
  results.forEach((item, idx) => {
    const isActive = idx === activeFeatureSearchIndex ? 'active' : '';
    const hlName = highlightSearchMatch(item.name, query);
    const hlDesc = highlightSearchMatch(item.description, query);
    const badgeHtml = item.badge 
      ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 ml-2 flex-shrink-0">${item.badge}</span>` 
      : '';

    html += `
      <a href="${item.link}" 
         class="search-feature-item ${isActive}" 
         data-index="${idx}" 
         onclick="handleFeatureSelect(event, '${item.link}')">
        <div class="feature-icon-box">
          <i class="${item.icon}"></i>
        </div>
        <div class="flex-1 min-w-0 pr-2">
          <div class="feature-item-title truncate">${hlName}</div>
          ${item.description ? `<div class="feature-item-desc">${hlDesc}</div>` : ''}
        </div>
        ${badgeHtml}
      </a>`;
  });

  container.innerHTML = html;

  const activeEl = container.querySelector('.search-feature-item.active');
  if (activeEl) {
    activeEl.scrollIntoView({ block: 'nearest' });
  }
}

function handleFeatureSelect(e, link) {
  if (e) e.preventDefault();
  closeFeatureSearchModal();
  if (link.startsWith('javascript:')) {
    const code = link.replace('javascript:', '');
    try {
      (new Function(code))();
    } catch (err) {
      console.error('Feature execution error:', err);
    }
  } else if (link.startsWith('http') || link.startsWith('//')) {
    window.open(link, '_blank');
  } else {
    window.location.href = link;
  }
}
window.handleFeatureSelect = handleFeatureSelect;

function updateActiveSearchItemIndex(newIndex) {
  if (filteredSearchResults.length === 0) return;
  activeFeatureSearchIndex = Math.max(0, Math.min(newIndex, filteredSearchResults.length - 1));
  const items = document.querySelectorAll('#featureSearchResults .search-feature-item');
  items.forEach(el => {
    const idx = parseInt(el.getAttribute('data-index'), 10);
    el.classList.toggle('active', idx === activeFeatureSearchIndex);
    if (idx === activeFeatureSearchIndex) {
      el.scrollIntoView({ block: 'nearest' });
    }
  });
}

function initFeatureSearch() {
  const sidebarInput = document.getElementById('sidebar-filter-input');
  if (sidebarInput) {
    sidebarInput.addEventListener('input', filterSidebarLinks);
    sidebarInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        const visibleLinks = document.querySelectorAll('#app-sidebar nav .sidebar-link:not([style*="display: none"])');
        if (visibleLinks.length === 1) {
          visibleLinks[0].click();
        } else {
          openFeatureSearchModal(this.value);
        }
      } else if (e.key === 'Escape') {
        clearSidebarFilter();
        this.blur();
      }
    });
  }

  const modalInput = document.getElementById('globalFeatureSearchInput');
  if (modalInput) {
    modalInput.addEventListener('input', function () {
      clearTimeout(featureSearchDebounce);
      const q = this.value;
      featureSearchDebounce = setTimeout(() => {
        performFeatureSearch(q);
      }, 100);
    });

    modalInput.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        updateActiveSearchItemIndex(activeFeatureSearchIndex + 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        updateActiveSearchItemIndex(activeFeatureSearchIndex - 1);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (activeFeatureSearchIndex >= 0 && filteredSearchResults[activeFeatureSearchIndex]) {
          const sel = filteredSearchResults[activeFeatureSearchIndex];
          handleFeatureSelect(null, sel.link);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeFeatureSearchModal();
      }
    });
  }

  // Global Shortcuts: Ctrl+/ (Focus Sidebar search) & Ctrl+K (Open Command Palette)
  document.addEventListener('keydown', function (e) {
    // Ctrl + / or Cmd + / -> focus sidebar search
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      const sbInput = document.getElementById('sidebar-filter-input');
      if (sbInput) {
        e.preventDefault();
        // If sidebar is collapsed, expand it
        if ($('#app-sidebar').hasClass('collapsed')) {
          $('#sidebar-toggle-btn').click();
        }
        sbInput.focus();
        sbInput.select();
      }
    }
    // Ctrl + K or Cmd + K -> open Command Palette
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      const modal = document.getElementById('featureSearchModal');
      if (modal && !modal.classList.contains('hidden')) {
        closeFeatureSearchModal();
      } else {
        openFeatureSearchModal();
      }
    }
  });

  // Pre-fetch catalog in background when browser is idle
  setTimeout(loadAllSystemFeatures, 1500);
}

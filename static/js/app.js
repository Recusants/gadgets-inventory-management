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
    confirmButtonColor: '#2563eb',
    background: $('html').hasClass('dark') ? '#0f172a' : '#ffffff',
    color: $('html').hasClass('dark') ? '#f8fafc' : '#0f172a',
    customClass: {
      popup: 'rounded-2xl shadow-2xl border border-slate-300 dark:border-slate-700'
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
    confirmButtonColor: '#ef4444',
    cancelButtonColor: '#64748b',
    confirmButtonText: confirmButtonText,
    cancelButtonText: 'Cancel',
    reverseButtons: true,
    background: $('html').hasClass('dark') ? '#0f172a' : '#ffffff',
    color: $('html').hasClass('dark') ? '#f8fafc' : '#0f172a',
    customClass: {
      popup: 'rounded-2xl shadow-2xl border border-slate-300 dark:border-slate-700'
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
    dialog.removeClass('max-w-xs max-w-sm max-w-md max-w-lg max-w-xl max-w-2xl max-w-3xl max-w-4xl max-w-5xl').addClass(sizeClass);
    
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
    
    // Serialize data
    const formData = $form.serialize();
    const actionUrl = $form.attr('action');
    const method = ($form.attr('method') || 'POST').toUpperCase();
    
    $.ajax({
      url: actionUrl,
      type: method,
      data: formData,
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest'
      },
      success: function (res) {
        $submitBtn.removeClass('btn-loading').prop('disabled', false);
        
        // SweetAlert2 notification according to uniform envelope
        if (!preventDefaultSwal) {
          notifySwal(res.title || 'Success', res.message || 'Operation successful', res.icon || 'success', 2200);
        }
        
        // Modal handling
        if (isModal) {
          ModalManager.close();
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
    });
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
  if ($icon.length) {
    if (isCollapsed) {
      $icon.removeClass('fa-bars').addClass('fa-bars-staggered');
    } else {
      $icon.removeClass('fa-bars-staggered').addClass('fa-bars');
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

  $(document).off('click', '#sidebar-toggle-btn')
    .on('click', '#sidebar-toggle-btn', function (e) {
      e.preventDefault();
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
    });
}


// Global Initialization
$(document).ready(function () {
  ModalManager.init();
  initAjaxForms();
  initDeleteActions();
  initSidebar();
  console.log('21 Void Technologies Core JS initialized successfully.');
});

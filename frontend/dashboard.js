
const API_BASE = window.DMS_API_BASE;
const token = sessionStorage.getItem('access_token');

let previewUrl = null;
let detailsVersion = 0;
let metadataVersion = 0;
let documentsVersion = 0;
let currentDetailsId = null;
let selectedMetadataDocument = null;

if (!token) {
  window.location.replace('index.html');
}

// =====================================
// COMMON HELPERS
// =====================================

function logout() {
  clearPreview();
  sessionStorage.removeItem('access_token');
  window.location.replace('index.html');
}

function showMessage(message, error = false) {
  const el = document.getElementById('dashboardMessage');
  el.textContent = message;
  el.style.color = error ? '#f87171' : '#2dd4bf';
}

function empty(container, message) {
  container.replaceChildren();

  const el = document.createElement('p');
  el.className = 'empty-state';
  el.textContent = message;
  container.append(el);
}

async function apiRequest(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.headers || {})
    }
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401 || response.status === 422) {
      logout();
      throw new Error('Session expired. Please log in again.');
    }

    throw new Error(
      data.error ||
      data.msg ||
      data.message ||
      `Request failed (${response.status})`
    );
  }

  return data;
}

const docsFrom = data =>
  Array.isArray(data)
    ? data
    : (data.documents || data.results || []);

const docId = doc =>
  doc.document_id || doc._id || doc.id;

function clearPreview() {
  const frame = document.getElementById('pdfPreview');

  frame.hidden = true;
  frame.removeAttribute('src');

  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }
}

// =====================================
// NAVIGATION
// =====================================

function showSection(id) {
  detailsVersion++;

  if (id !== 'details') {
    clearPreview();
  }

  document.querySelectorAll('.dashboard-section').forEach(section => {
    section.hidden = section.id !== id;
  });

  document.querySelectorAll('.nav-item').forEach(button => {
    button.classList.toggle(
      'active',
      button.dataset.section === id
    );
  });

  const titles = {
    overview: 'Overview',
    documents: 'All Documents',
    upload: 'Upload Center',
    search: 'Smart Search',
    requests: 'Access Requests',
    metadata: 'Custom Metadata',
    details: 'Document Details'
  };

  document.getElementById('breadcrumb').textContent =
    `Workspace / ${titles[id] || id}`;

  showMessage('');

  if (id === 'overview') loadOverview();
  if (id === 'documents') loadDocuments();
  if (id === 'requests') loadPendingRequests();
  if (id === 'metadata') loadMetadataDocuments();
}

// =====================================
// DOCUMENT LIST AND ACCESS BUTTONS
// =====================================

function renderDocuments(containerId, documents, limit = null) {
  const container = document.getElementById(containerId);
  container.replaceChildren();

  const visible = limit
    ? documents.slice(0, limit)
    : documents;

  if (!visible.length) {
    empty(container, 'No documents available.');
    return;
  }

  visible.forEach(doc => {
    const id = docId(doc);
    const status = doc.access_status || 'accessible';

    const row = document.createElement('div');
    row.className = 'document-item';

    const info = document.createElement('div');
    info.className = 'document-row-info';

    const name = document.createElement('strong');
    name.textContent = doc.filename || 'Untitled document';

    const meta = document.createElement('p');
    meta.className = 'muted-paragraph';

    meta.textContent =
      `Division: ${doc.division || 'Unknown'} · ` +
      `Access: ${status}` +
      (doc.metadata?.category
        ? ` · Category: ${doc.metadata.category}`
        : '');

    info.append(name, meta);

    const actions = document.createElement('div');
    actions.className = 'document-row-actions';

    if (status === 'accessible' || status === 'approved') {
      const view = document.createElement('button');
      view.textContent = 'View Details';
      view.disabled = !id;
      view.onclick = () => openDocumentDetails(id);

      const download = document.createElement('button');
      download.textContent = 'Download';
      download.disabled = !id;
      download.onclick = () => downloadDocument(id, doc.filename);

      actions.append(view, download);

    } else if (status === 'pending') {
      const pending = document.createElement('button');
      pending.textContent = 'Pending Approval';
      pending.disabled = true;
      actions.append(pending);

    } else {
      const request = document.createElement('button');
      request.textContent = 'Request Access';
      request.disabled = !id;
      request.onclick = () => requestDocumentAccess(id, request);

      actions.append(request);
    }

    row.append(info, actions);
    container.append(row);
  });
}

// =====================================
// REQUEST DOCUMENT ACCESS
// =====================================

async function requestDocumentAccess(id, button) {
  button.disabled = true;
  button.textContent = 'Requesting...';

  try {
    await apiRequest('/access/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        doc_id: id
      })
    });

    button.textContent = 'Pending Approval';

    await loadDocuments();

    showMessage('Access request submitted successfully!');
  } catch (error) {
    button.disabled = false;
    button.textContent = 'Request Access';
    showMessage(error.message, true);
  }
}

// =====================================
// OVERVIEW
// =====================================

async function loadOverview() {
  try {
    const docs = docsFrom(
      await apiRequest('/documents/')
    );

    document.getElementById('totalDocuments').textContent =
      docs.length;

    renderDocuments('recentDocuments', docs, 5);
  } catch (error) {
    showMessage(error.message, true);
  }

  try {
    const data = await apiRequest('/access/pending');

    const requests = Array.isArray(data)
      ? data
      : data.requests || [];

    document.getElementById('pendingCount').textContent =
      requests.length;
  } catch (error) {
    document.getElementById('pendingCount').textContent = '—';
    showMessage(error.message, true);
  }
}

// =====================================
// DYNAMIC METADATA FILTERING
// =====================================

function buildDocumentFilterPath() {
  const field = document.getElementById('filterField').value.trim();
  const value = document.getElementById('filterValue').value.trim();

  if (!field && !value) {
    return '/documents/';
  }

  if (!field || !value) {
    throw new Error(
      'Enter both a metadata field and its value.'
    );
  }

  if (
    field.startsWith('$') ||
    field.includes('.') ||
    ['__proto__', 'constructor', 'prototype'].includes(field)
  ) {
    throw new Error('Invalid metadata field name.');
  }

  const params = new URLSearchParams();
  params.append(field, value);

  return '/documents/?' + params.toString();
}

async function loadDocuments() {
  const version = ++documentsVersion;
  const container = document.getElementById('documentList');
  const status = document.getElementById('filterStatus');

  empty(container, 'Loading documents...');

  try {
    const filterPath = buildDocumentFilterPath();

    // Discover documents from all divisions when no
    // metadata filter is applied.
    // Filtered results use the existing protected API.
    const path = filterPath === '/documents/'
      ? '/documents/discover'
      : filterPath;

    const data = await apiRequest(path);

    if (version !== documentsVersion) return;

    const documents = docsFrom(data);

    renderDocuments('documentList', documents);

    status.textContent =
      `Showing ${documents.length} document(s).`;

  } catch (error) {
    if (version !== documentsVersion) return;

    empty(container, 'Unable to load documents.');

    status.textContent = 'Unable to load documents.';
    showMessage(error.message, true);
  }
}

function clearDocumentFilters() {
  document.getElementById('filterField').value = '';
  document.getElementById('filterValue').value = '';
  loadDocuments();
}

document.getElementById('documentFilterForm')
  .addEventListener('submit', event => {
    event.preventDefault();
    loadDocuments();
  });

// =====================================
// UPLOAD DOCUMENT
// =====================================

document.getElementById('uploadForm')
  .addEventListener('submit', async event => {
    event.preventDefault();

    const file =
      document.getElementById('documentFile').files[0];

    if (!file) {
      return showMessage('Choose a file.', true);
    }

    if (file.size > 15 * 1024 * 1024) {
      return showMessage('File exceeds 15 MB.', true);
    }

    const form = new FormData();

    form.append('file', file);

    form.append('metadata', JSON.stringify({
      category:
        document.getElementById('category').value.trim() ||
        'General'
    }));

    const button =
      event.target.querySelector('button[type=submit]');

    button.disabled = true;

    try {
      await apiRequest('/documents/upload', {
        method: 'POST',
        body: form
      });

      event.target.reset();

      showMessage('Document uploaded successfully.');
    } catch (error) {
      showMessage(error.message, true);
    } finally {
      button.disabled = false;
    }
  });

// =====================================
// OCR AND DOCUMENT SEARCH
// =====================================

async function searchDocuments() {
  const q =
    document.getElementById('searchInput').value.trim();

  if (!q) {
    return showMessage('Enter a search term.', true);
  }

  try {
    const docs = docsFrom(
      await apiRequest(
        '/search?q=' + encodeURIComponent(q)
      )
    );

    renderDocuments('searchResults', docs);

    showMessage(`${docs.length} document(s) found.`);
  } catch (error) {
    showMessage(error.message, true);
  }
}

document.getElementById('searchInput')
  .addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      searchDocuments();
    }
  });

// =====================================
// SECURE DOCUMENT DOWNLOAD
// =====================================

async function downloadDocument(id, filename = 'document') {
  try {
    const response = await fetch(
      `${API_BASE}/documents/${id}/download`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    );

    if (!response.ok) {
      if ([401, 422].includes(response.status)) {
        return logout();
      }

      const error =
        await response.json().catch(() => ({}));

      throw new Error(
        error.error || 'Download failed.'
      );
    }

    const url = URL.createObjectURL(
      await response.blob()
    );

    const a = document.createElement('a');

    a.href = url;
    a.download = filename;

    document.body.append(a);
    a.click();
    a.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);

    showMessage('Download started.');
  } catch (error) {
    showMessage(error.message, true);
  }
}

// =====================================
// DOCUMENT DETAILS
// =====================================

function addDetail(container, label, value) {
  const row = document.createElement('div');
  row.className = 'detail-field';

  const key = document.createElement('span');
  key.className = 'detail-field-label';
  key.textContent = label;

  const val = document.createElement('span');
  val.className = 'detail-field-value';

  val.textContent =
    value == null || value === ''
      ? 'Not available'
      : typeof value === 'object'
        ? JSON.stringify(value)
        : String(value);

  row.append(key, val);
  container.append(row);
}

async function openDocumentDetails(id) {
  showSection('details');

  const version = detailsVersion;
  currentDetailsId = id;

  document.getElementById('detailFilename').textContent =
    'Loading document...';

  document.getElementById('detailDivision').textContent = '';

  ['documentInfo', 'documentMetadata'].forEach(key => {
    document.getElementById(key).replaceChildren();
  });

  document.getElementById('documentOCR').textContent = '';

  const download =
    document.getElementById('detailDownloadButton');

  const edit =
    document.getElementById('editDetailsMetadataButton');

  download.disabled = true;
  edit.disabled = true;

  const status = document.getElementById('previewStatus');

  status.hidden = false;
  status.textContent = 'Loading preview...';

  try {
    const doc = await apiRequest(`/documents/${id}`);

    if (version !== detailsVersion) return;

    document.getElementById('detailFilename').textContent =
      doc.filename || 'Untitled document';

    document.getElementById('detailDivision').textContent =
      `Division: ${doc.division || 'Unknown'}`;

    const info = document.getElementById('documentInfo');

    addDetail(info, 'Filename', doc.filename);
    addDetail(info, 'Division', doc.division);
    addDetail(info, 'Document ID', doc.document_id);
    addDetail(info, 'Owner ID', doc.owner_id);

    addDetail(
      info,
      'Uploaded At',
      doc.created_at
        ? new Date(doc.created_at).toLocaleString()
        : null
    );

    const metadata =
      document.getElementById('documentMetadata');

    const entries = Object.entries(
      doc.metadata || {}
    );

    if (!entries.length) {
      addDetail(
        metadata,
        'Metadata',
        'No metadata available'
      );
    } else {
      entries.forEach(([key, value]) => {
        addDetail(metadata, key, value);
      });
    }

    document.getElementById('documentOCR').textContent =
      doc.extracted_text ||
      'No extracted text available.';

    download.disabled = false;
    download.onclick = () =>
      downloadDocument(id, doc.filename);

    edit.disabled = false;
    edit.onclick = () => {
      document.getElementById(
        'metadataDocumentSelect'
      ).dataset.preselect = id;

      showSection('metadata');
    };

    await loadPreview(
      id,
      doc.filename || '',
      version
    );
  } catch (error) {
    if (version !== detailsVersion) return;

    document.getElementById('detailFilename').textContent =
      'Unable to load document';

    status.hidden = false;
    status.textContent = 'Preview unavailable.';

    showMessage(error.message, true);
  }
}

// =====================================
// PDF PREVIEW
// =====================================

async function loadPreview(id, filename, version) {
  const status =
    document.getElementById('previewStatus');

  if (!filename.toLowerCase().endsWith('.pdf')) {
    status.textContent =
      'Inline preview is available for PDF files only.';
    return;
  }

  try {
    const response = await fetch(
      `${API_BASE}/documents/${id}/preview`,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    );

    if (!response.ok) {
      if ([401, 422].includes(response.status)) {
        return logout();
      }

      const error =
        await response.json().catch(() => ({}));

      throw new Error(
        error.error || 'Preview unavailable.'
      );
    }

    const blob = await response.blob();

    if (version !== detailsVersion) return;

    clearPreview();

    previewUrl = URL.createObjectURL(blob);

    const frame =
      document.getElementById('pdfPreview');

    frame.src = previewUrl;
    frame.hidden = false;

    status.hidden = true;
  } catch (error) {
    if (version !== detailsVersion) return;

    status.hidden = false;
    status.textContent = error.message;
  }
}

// =====================================
// ACCESS REQUEST INBOX
// =====================================

async function loadPendingRequests() {
  const container =
    document.getElementById('requestList');

  empty(container, 'Loading pending requests...');

  try {
    const data =
      await apiRequest('/access/pending');

    const requests = Array.isArray(data)
      ? data
      : data.requests || [];

    container.replaceChildren();

    if (!requests.length) {
      return empty(
        container,
        'No pending requests.'
      );
    }

    requests.forEach(request => {
      const id =
        request.request_id ||
        request._id ||
        request.id;

      const row = document.createElement('div');
      row.className = 'document-item';

      const label = document.createElement('span');

      label.textContent =
        `Request ${id || ''} · ` +
        `${request.status || 'pending'}`;

      const actions = document.createElement('div');
      actions.className = 'document-row-actions';

      ['approved', 'rejected'].forEach(decision => {
        const button = document.createElement('button');

        button.textContent =
          decision === 'approved'
            ? 'Approve'
            : 'Reject';

        button.disabled = !id;

        button.onclick = () =>
          decideRequest(id, decision);

        actions.append(button);
      });

      row.append(label, actions);
      container.append(row);
    });
  } catch (error) {
    empty(
      container,
      'Unable to load requests.'
    );

    showMessage(error.message, true);
  }
}

async function decideRequest(id, decision) {
  try {
    await apiRequest(
      `/access/${id}/decision`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          decision
        })
      }
    );

    await loadPendingRequests();

    showMessage(`Request ${decision}.`);
  } catch (error) {
    showMessage(error.message, true);
  }
}

// =====================================
// CUSTOM METADATA EDITOR
// =====================================

async function loadMetadataDocuments(preselect = null) {
  const version = ++metadataVersion;

  const select =
    document.getElementById('metadataDocumentSelect');

  const chosen =
    preselect ||
    select.dataset.preselect ||
    select.value;

  select.replaceChildren(
    new Option('Loading documents...', '')
  );

  setMetadataEditing(false);

  document.getElementById(
    'metadataFields'
  ).replaceChildren();

  document.getElementById(
    'metadataEditorStatus'
  ).textContent = 'Loading documents...';

  try {
    const docs = docsFrom(
      await apiRequest('/documents/')
    );

    if (version !== metadataVersion) return;

    select.replaceChildren(
      new Option('Select a document', '')
    );

    docs.forEach(doc => {
      const id = docId(doc);

      if (id) {
        select.add(
          new Option(
            `${doc.filename || 'Document'} ` +
            `(${doc.division || 'Unknown'})`,
            id
          )
        );
      }
    });

    if (
      chosen &&
      docs.some(doc => docId(doc) === chosen)
    ) {
      select.value = chosen;
    }

    delete select.dataset.preselect;

    if (select.value) {
      await loadMetadataForSelection();
    } else {
      document.getElementById(
        'metadataEditorStatus'
      ).textContent = docs.length
        ? 'Choose a document to edit its metadata.'
        : 'No accessible documents.';
    }
  } catch (error) {
    document.getElementById(
      'metadataEditorStatus'
    ).textContent = error.message;

    showMessage(error.message, true);
  }
}

function setMetadataEditing(enabled) {
  document.getElementById(
    'addMetadataField'
  ).disabled = !enabled;

  document.getElementById(
    'saveMetadataButton'
  ).disabled = !enabled;
}

document.getElementById(
  'metadataDocumentSelect'
).addEventListener(
  'change',
  loadMetadataForSelection
);

async function loadMetadataForSelection() {
  const version = ++metadataVersion;

  const id = document.getElementById(
    'metadataDocumentSelect'
  ).value;

  selectedMetadataDocument = null;
  setMetadataEditing(false);

  const fields =
    document.getElementById('metadataFields');

  fields.replaceChildren();

  const status = document.getElementById(
    'metadataEditorStatus'
  );

  if (!id) {
    status.textContent = 'Choose a document.';
    return;
  }

  status.textContent = 'Loading metadata...';

  try {
    const doc =
      await apiRequest(`/documents/${id}`);

    if (version !== metadataVersion) return;

    selectedMetadataDocument = id;

    const entries = Object.entries(
      doc.metadata || {}
    );

    entries.forEach(([key, value]) => {
      addMetadataRow(
        key,
        typeof value === 'string'
          ? value
          : JSON.stringify(value)
      );
    });

    status.textContent =
      `Editing: ${doc.filename}. ` +
      'Only the document owner can save changes.';

    setMetadataEditing(true);
  } catch (error) {
    if (version !== metadataVersion) return;

    status.textContent = error.message;
    showMessage(error.message, true);
  }
}

function addMetadataRow(key = '', value = '') {
  if (
    !selectedMetadataDocument &&
    !document.getElementById(
      'metadataDocumentSelect'
    ).value
  ) {
    return;
  }

  const row = document.createElement('div');
  row.className = 'metadata-row';

  const name = document.createElement('input');
  name.type = 'text';
  name.className = 'metadata-key';
  name.placeholder = 'Field name (e.g. Priority)';
  name.value = key;

  name.setAttribute(
    'aria-label',
    'Metadata field name'
  );

  const val = document.createElement('input');
  val.type = 'text';
  val.className = 'metadata-value';
  val.placeholder = 'Value (e.g. High)';
  val.value = value;

  val.setAttribute(
    'aria-label',
    'Metadata value'
  );

  const remove = document.createElement('button');
  remove.type = 'button';
  remove.textContent = 'Remove';

  remove.onclick = () => row.remove();

  row.append(name, val, remove);

  document.getElementById(
    'metadataFields'
  ).append(row);
}

async function saveDocumentMetadata() {
  if (!selectedMetadataDocument) {
    return showMessage(
      'Select a document first.',
      true
    );
  }

  const metadata = {};

  const rows = document.querySelectorAll(
    '#metadataFields .metadata-row'
  );

  for (const row of rows) {
    const key = row.querySelector(
      '.metadata-key'
    ).value.trim();

    const value = row.querySelector(
      '.metadata-value'
    ).value.trim();

    if (!key) {
      return showMessage(
        'Every metadata row needs a field name. ' +
        'Remove empty rows.',
        true
      );
    }

    if (
      key.startsWith('$') ||
      key.includes('.')
    ) {
      return showMessage(
        'Field names cannot start with $ or contain a dot.',
        true
      );
    }

    if (
      Object.prototype.hasOwnProperty.call(
        metadata,
        key
      )
    ) {
      return showMessage(
        `Duplicate field: ${key}`,
        true
      );
    }

    if (
      ['__proto__', 'constructor', 'prototype'].includes(key)
    ) {
      return showMessage(
        `Reserved field name: ${key}`,
        true
      );
    }

    metadata[key] = value;
  }

  const button = document.getElementById(
    'saveMetadataButton'
  );

  button.disabled = true;
  button.textContent = 'Saving...';

  try {
    await apiRequest(
      `/documents/${selectedMetadataDocument}/metadata`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          metadata
        })
      }
    );

    showMessage(
      'Metadata saved successfully!'
    );

    document.getElementById(
      'metadataEditorStatus'
    ).textContent =
      'Saved. Changes are stored in MongoDB.';
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = 'Save Metadata';
  }
}

// =====================================
// INITIALIZE DASHBOARD
// =====================================

if (token) {
  showSection('overview');
}

window.addEventListener(
  'beforeunload',
  clearPreview
);

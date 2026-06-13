// LiverLink - Hackathon Demo Simulation Logic

// ==========================================
// 1. Initial State & Data Definitions
// ==========================================

const patientsData = {
  "John Doe": {
    name: "John Doe",
    diagnosis: "NASH Stage 2",
    medication: "Ursodiol 300mg",
    frequency: "2 times daily (with breakfast & dinner)",
    timelineDays: 45,
    timelineTotal: 90,
    healthStatus: 82,
    reminders: [
      { id: "jd-med-1", name: "Ursodiol 300mg - Morning Dose", time: "08:00 AM", completed: true },
      { id: "jd-med-2", name: "Ursodiol 300mg - Evening Dose", time: "08:00 PM", completed: false },
      { id: "jd-water", name: "Water Intake Target (2.5 Liters)", time: "09:00 PM", completed: false }
    ],
    biochemistry: [
      { date: "May 10", alt: 72, ast: 64, bilirubin: 1.6, orderedBy: "Dr. Vance", status: "Completed" },
      { date: "May 25", alt: 58, ast: 50, bilirubin: 1.3, orderedBy: "Dr. Vance", status: "Completed" },
      { date: "June 08", alt: 48, ast: 42, bilirubin: 1.1, orderedBy: "Dr. Vance", status: "Completed" }
    ],
    symptoms: {
      fatigue: "Mild",
      nausea: "None",
      jaundice: "No"
    }
  },
  "Sarah Connor": {
    name: "Sarah Connor",
    diagnosis: "Early Liver Cirrhosis",
    medication: "Obeticholic Acid 5mg",
    frequency: "Once daily in the morning",
    timelineDays: 20,
    timelineTotal: 60,
    healthStatus: 74,
    reminders: [
      { id: "sc-med-1", name: "Obeticholic Acid 5mg - Morning Dose", time: "09:00 AM", completed: true },
      { id: "sc-water", name: "Water Intake Target (2.0 Liters)", time: "09:00 PM", completed: true }
    ],
    biochemistry: [
      { date: "May 15", alt: 95, ast: 82, bilirubin: 2.1, orderedBy: "Dr. Vance", status: "Completed" },
      { date: "June 01", alt: 84, ast: 76, bilirubin: 1.8, orderedBy: "Dr. Vance", status: "Completed" }
    ],
    symptoms: {
      fatigue: "Moderate",
      nausea: "Mild bloating",
      jaundice: "No"
    }
  }
};

// Global App State
const state = {
  currentPatient: "John Doe",
  activeRole: "patient",
  labOrders: [
    { id: "ORD-9821", patient: "John Doe", panel: "Comprehensive Liver Function Panel", date: "June 13, 2026", status: "Pending" }
  ],
  agentLogs: [
    { timestamp: getFormattedTime(120), text: "LiverLink Patient Agent initialized for John Doe.", type: "success" },
    { timestamp: getFormattedTime(60), text: "Agent sync check: Patient completed Ursodiol Morning Dose (08:00 AM).", type: "success" },
    { timestamp: getFormattedTime(5), text: "Agent telemetry: Vitals stable. AST/ALT indices trending downwards.", type: "info" }
  ]
};

// ==========================================
// 2. Navigation & View Switching
// ==========================================

function scrollToSelector() {
  const el = document.getElementById('selector-section');
  if (el) el.scrollIntoView({ behavior: 'smooth' });
}

function scrollToStats() {
  const el = document.getElementById('stats-section');
  if (el) el.scrollIntoView({ behavior: 'smooth' });
}

function openDashboard(role) {
  state.activeRole = role;
  
  // Set UI elements
  const overlay = document.getElementById('dashboard-overlay');
  const landing = document.getElementById('landing-page');
  const badge = document.getElementById('active-role-badge');
  
  badge.textContent = role.toUpperCase();
  badge.className = `role-badge ${getRoleBadgeClass(role)}`;
  
  // Hide all dashboard views
  document.querySelectorAll('.dashboard-view').forEach(view => {
    view.classList.remove('active');
  });
  
  // Show selected dashboard view
  const targetView = document.getElementById(`view-${role}`);
  if (targetView) targetView.classList.add('active');
  
  // Show overlay modal
  overlay.classList.add('active');
  document.body.style.overflow = 'hidden'; // Lock background scroll
  
  // Render specific role components
  renderDashboard(role);
  showToast("Portal Connection Established", `Switched to the ${role} dashboard view.`);
}

function closeDashboard() {
  const overlay = document.getElementById('dashboard-overlay');
  overlay.classList.remove('active');
  document.body.style.overflow = 'auto'; // Unlock scroll
}

function getRoleBadgeClass(role) {
  switch(role) {
    case 'patient': return 'cyan-grad';
    case 'caregiver': return 'emerald-grad';
    case 'doctor': return 'teal-grad';
    case 'lab': return 'mint-grad';
    default: return '';
  }
}

// ==========================================
// 3. Render Dashboard Views
// ==========================================

function renderDashboard(role) {
  const patient = patientsData[state.currentPatient];
  
  if (role === 'patient') {
    renderPatientDashboard(patient);
  } else if (role === 'caregiver') {
    renderCaregiverDashboard(patient);
  } else if (role === 'doctor') {
    renderDoctorDashboard(patient);
  } else if (role === 'lab') {
    renderLabDashboard();
  }
}

// Patient View Rendering
function renderPatientDashboard(patient) {
  // Set summary info
  document.getElementById('patient-med-name').textContent = patient.medication;
  document.getElementById('patient-med-frequency').textContent = patient.frequency;
  document.getElementById('patient-timeline-days').textContent = patient.timelineDays;
  
  const percentage = Math.round((patient.timelineDays / patient.timelineTotal) * 100);
  document.getElementById('patient-timeline-bar').style.width = `${percentage}%`;
  
  // Update lab status flag in patient view
  const hasPending = state.labOrders.some(o => o.patient === patient.name && o.status === 'Pending');
  const labStatusEl = document.getElementById('patient-lab-status');
  if (hasPending) {
    labStatusEl.textContent = "Pending Bloodwork";
    labStatusEl.className = "metric-value text-danger";
  } else {
    labStatusEl.textContent = "Completed & Checked";
    labStatusEl.className = "metric-value text-success";
  }

  // Populate reminders checklist
  const listEl = document.getElementById('patient-reminders-list');
  listEl.innerHTML = '';
  
  patient.reminders.forEach(reminder => {
    const item = document.createElement('div');
    item.className = `reminder-item ${reminder.completed ? 'completed' : ''}`;
    item.innerHTML = `
      <div class="reminder-info">
        <span class="reminder-time">${reminder.time}</span>
        <div class="reminder-med-details">
          <strong class="reminder-name">${reminder.name}</strong>
          <span class="reminder-dosage">Status: ${reminder.completed ? 'Taken' : 'Awaiting confirmation'}</span>
        </div>
      </div>
      <button class="btn-checkbox" onclick="toggleReminder('${reminder.id}')" aria-label="Toggle reminder">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      </button>
    `;
    listEl.appendChild(item);
  });
}

// Caregiver View Rendering
function renderCaregiverDashboard(patient) {
  // Update patient vitals
  document.getElementById('caregiver-last-symptom').textContent = `${patient.symptoms.fatigue} Fatigue / ${patient.symptoms.nausea}`;
  
  // Calculate compliance percentage
  const total = patient.reminders.length;
  const completed = patient.reminders.filter(r => r.completed).length;
  const adherence = total > 0 ? Math.round((completed / total) * 100) : 100;
  
  const adherenceEl = document.getElementById('caregiver-adherence-val');
  adherenceEl.textContent = `${adherence}%`;
  adherenceEl.className = `val ${adherence >= 80 ? 'text-success' : 'text-danger'}`;
  
  // Load logs
  renderAgentLogs();
}

function renderAgentLogs() {
  const container = document.getElementById('agent-logs-list');
  container.innerHTML = '';
  
  state.agentLogs.forEach(log => {
    const item = document.createElement('div');
    item.className = `agent-log-item ${log.type}`;
    item.innerHTML = `<span class="timestamp">[${log.timestamp}]</span> ${log.text}`;
    container.appendChild(item);
  });
  
  // Scroll to bottom
  container.scrollTop = container.scrollHeight;
}

// Doctor View Rendering
function renderDoctorDashboard(patient) {
  document.getElementById('doctor-detail-patient-name').textContent = `Patient Health Chart: ${patient.name}`;
  
  // Set current prescription selects to match patient
  document.getElementById('doctor-prescribe-med').value = patient.medication;
  document.getElementById('doctor-prescribe-freq').value = patient.frequency;
  
  // Populate biochemical records table
  const tbody = document.getElementById('doctor-lab-records-tbody');
  tbody.innerHTML = '';
  
  // Show records in reverse chronological order
  [...patient.biochemistry].reverse().forEach(record => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${record.date}</td>
      <td class="${record.alt > 35 ? 'text-danger' : 'text-success'}">${record.alt} U/L</td>
      <td class="${record.ast > 40 ? 'text-danger' : 'text-success'}">${record.ast} U/L</td>
      <td class="${record.bilirubin > 1.2 ? 'text-danger' : 'text-success'}">${record.bilirubin} mg/dL</td>
      <td>${record.orderedBy}</td>
      <td><span class="badge ${record.status === 'Completed' ? 'badge-success' : 'badge-warning'}">${record.status}</span></td>
    `;
    tbody.appendChild(tr);
  });

  // Render SVG Enzyme Trend Chart
  renderBiochemicalChart(patient.biochemistry);
}

// Lab View Rendering
function renderLabDashboard() {
  const tbody = document.getElementById('lab-worklist-tbody');
  tbody.innerHTML = '';
  
  if (state.labOrders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-muted" style="text-align: center;">No diagnostic requests in worklist.</td></tr>`;
    document.getElementById('lab-pending-badge').textContent = "0 Pending Panels";
    document.getElementById('lab-pending-badge').className = "badge badge-success";
    return;
  }
  
  const pendingCount = state.labOrders.filter(o => o.status === 'Pending').length;
  document.getElementById('lab-pending-badge').textContent = `${pendingCount} Pending Panel${pendingCount !== 1 ? 's' : ''}`;
  document.getElementById('lab-pending-badge').className = pendingCount > 0 ? "badge badge-purple" : "badge badge-success";

  state.labOrders.forEach(order => {
    const tr = document.createElement('tr');
    const actionBtn = order.status === 'Pending' 
      ? `<button class="btn btn-small btn-primary" onclick="simulateLabAnalysis('${order.id}')">🔬 Process Sample</button>`
      : `<span class="text-success">Processed</span>`;
      
    tr.innerHTML = `
      <td><strong>${order.id}</strong></td>
      <td>${order.patient}</td>
      <td>${order.panel}</td>
      <td>${order.date}</td>
      <td><span class="badge ${order.status === 'Pending' ? 'badge-purple' : 'badge-success'}">${order.status}</span></td>
      <td>${actionBtn}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ==========================================
// 4. Action Handlers (Patient & Caregiver)
// ==========================================

function toggleReminder(id) {
  const patient = patientsData[state.currentPatient];
  const reminder = patient.reminders.find(r => r.id === id);
  if (reminder) {
    reminder.completed = !reminder.completed;
    
    // Add caregiver log
    const action = reminder.completed ? "completed" : "uncompleted";
    addAgentLog(`Patient checked off checklist item: ${reminder.name} (${action}).`, reminder.completed ? "success" : "info");
    
    // Refresh UI
    renderPatientDashboard(patient);
    showToast("Progress Synchronized", `Updated reminder checkbox.`);
  }
}

function logSymptom(event) {
  event.preventDefault();
  const patient = patientsData[state.currentPatient];
  
  const fatigue = document.getElementById('symptom-fatigue').value;
  const nausea = document.getElementById('symptom-nausea').value;
  const jaundice = document.getElementById('symptom-jaundice').value;
  
  patient.symptoms.fatigue = fatigue;
  patient.symptoms.nausea = nausea;
  patient.symptoms.jaundice = jaundice;
  
  // Agent logging
  addAgentLog(`Patient logged symptoms: Fatigue [${fatigue}], Nausea/Pain [${nausea}], Jaundice Signs [${jaundice}].`, jaundice === 'Yes' ? 'alert' : 'info');
  
  if (jaundice === 'Yes' || nausea === 'Severe') {
    addAgentLog(`[CRITICAL WARNING] LiverLink Patient Agent detected high risk factors. Clinical dispatch warning sent to Dr. Vance.`, 'alert');
    showToast("Clinical Warning Triggered", "Severe symptoms recorded. Alert dispatched to Dr. Vance.", true);
  } else {
    showToast("Symptom Logged", "Log updated and sent to Caregiver & Doctor.");
  }
  
  renderPatientDashboard(patient);
}

function triggerCaregiverNudge() {
  addAgentLog("Caregiver sent manual medication reminder nudge to Patient's screen.", "info");
  showToast("Medication Nudge Dispatched", "Patient will receive an alert reminder.");
}

function triggerCaregiverCall() {
  addAgentLog("Caregiver logged successful phone check-in with patient.", "success");
  showToast("Activity Recorded", "Phone call validation logged in system.");
}

function triggerEmergencyAlert() {
  addAgentLog("[EMERGENCY TRIGGER] Caregiver initiated direct clinic alert! Dr. Vance notified for check-up request.", "alert");
  showToast("Clinic Alert Dispatched", "Emergency signal broadcasted to Doctor Vance's terminal.", true);
}

function clearAgentLogs() {
  state.agentLogs = [];
  addAgentLog("Activity logs cleared by Caregiver.", "info");
  renderAgentLogs();
}

// ==========================================
// 5. Action Handlers (Doctor)
// ==========================================

function selectDoctorPatient(name) {
  state.currentPatient = name;
  
  // Set selectors
  document.querySelectorAll('.active-patient-selector').forEach(sel => {
    sel.classList.remove('active');
    const patName = sel.querySelector('strong').textContent;
    if (patName === name) sel.classList.add('active');
  });
  
  const patient = patientsData[name];
  renderDoctorDashboard(patient);
  
  // Set inputs in lab result entry to match patient selector
  document.getElementById('lab-result-patient').value = name;
  
  showToast("Patient Selected", `Now reviewing clinical charts for ${name}.`);
}

function applyPrescriptionChange() {
  const patient = patientsData[state.currentPatient];
  const med = document.getElementById('doctor-prescribe-med').value;
  const freq = document.getElementById('doctor-prescribe-freq').value;
  
  patient.medication = med;
  patient.frequency = freq;
  patient.timelineDays = 0; // Reset treatment timeline for new course
  
  // Re-generate patient reminders for new medication
  if (state.currentPatient === "John Doe") {
    patient.reminders = [
      { id: "jd-med-1", name: `${med} - Dose A`, time: "08:00 AM", completed: false },
      { id: "jd-med-2", name: `${med} - Dose B`, time: "08:00 PM", completed: false }
    ];
  } else {
    patient.reminders = [
      { id: "sc-med-1", name: `${med} - Daily Dose`, time: "09:00 AM", completed: false }
    ];
  }
  
  addAgentLog(`Dr. Vance updated patient medication to ${med} (${freq}). Previous schedule deleted.`, "info");
  showToast("Prescription Updated", `Patient therapy regimen modified successfully.`);
  
  renderDoctorDashboard(patient);
}

function requestLabTest() {
  const panel = document.getElementById('doctor-lab-panel').value;
  const patient = state.currentPatient;
  const orderId = "ORD-" + Math.floor(1000 + Math.random() * 9000);
  
  const newOrder = {
    id: orderId,
    patient: patient,
    panel: panel,
    date: "June 13, 2026",
    status: "Pending"
  };
  
  state.labOrders.push(newOrder);
  addAgentLog(`Dr. Vance requested diagnostic panel [${panel}] for patient ${patient}. Order ID: ${orderId}`, "info");
  showToast("Diagnostic Requested", `Lab panel ordered. Check Central Lab Portal.`);
  
  renderDoctorDashboard(patientsData[patient]);
}

// ==========================================
// 6. Action Handlers (Lab Portal)
// ==========================================

function simulateLabAnalysis(orderId) {
  const order = state.labOrders.find(o => o.id === orderId);
  if (!order) return;
  
  const panelEl = document.getElementById('lab-simulation-panel');
  panelEl.classList.remove('hidden');
  
  const container = panelEl.querySelector('.analyzer-animation-container');
  container.classList.add('analyzing');
  
  const progressEl = document.getElementById('lab-sim-progress');
  const statusTextEl = document.getElementById('analyzer-text-status');
  
  // Lock submit button during simulation
  const submitBtn = document.getElementById('lab-submit-btn');
  submitBtn.disabled = true;
  
  let progress = 0;
  statusTextEl.textContent = "Centrifuging blood serum...";
  
  const interval = setInterval(() => {
    progress += 4;
    progressEl.style.width = `${progress}%`;
    
    if (progress === 40) {
      statusTextEl.textContent = "Incubating liver biochemistry panel...";
    } else if (progress === 72) {
      statusTextEl.textContent = "Spectrophotometric enzyme evaluation...";
    } else if (progress >= 100) {
      clearInterval(interval);
      container.classList.remove('analyzing');
      statusTextEl.textContent = "Analysis completed. Input markers generated.";
      
      // Auto-fill values with slightly optimized but realistic markers for John/Sarah
      if (order.patient === "John Doe") {
        document.getElementById('lab-result-alt').value = 38; // Improving trend
        document.getElementById('lab-result-ast').value = 39;
        document.getElementById('lab-result-bilirubin').value = 1.0;
      } else {
        document.getElementById('lab-result-alt').value = 75; // Still elevated
        document.getElementById('lab-result-ast').value = 68;
        document.getElementById('lab-result-bilirubin').value = 1.5;
      }
      
      document.getElementById('lab-result-patient').value = order.patient;
      document.getElementById('lab-result-panel-name').value = order.panel;
      
      submitBtn.disabled = false;
      showToast("Analysis Complete", "Bio-markers populated in the submission card.");
    }
  }, 100);
}

function submitLabResults(event) {
  event.preventDefault();
  
  const patientName = document.getElementById('lab-result-patient').value;
  const panelName = document.getElementById('lab-result-panel-name').value;
  const alt = parseInt(document.getElementById('lab-result-alt').value);
  const ast = parseInt(document.getElementById('lab-result-ast').value);
  const bilirubin = parseFloat(document.getElementById('lab-result-bilirubin').value);
  
  // Find pending order and mark completed
  const orderIndex = state.labOrders.findIndex(o => o.patient === patientName && o.status === 'Pending');
  if (orderIndex !== -1) {
    state.labOrders[orderIndex].status = "Completed";
  }
  
  // Append new biochemistry record
  const patient = patientsData[patientName];
  patient.biochemistry.push({
    date: "June 13",
    alt: alt,
    ast: ast,
    bilirubin: bilirubin,
    orderedBy: "Dr. Vance",
    status: "Completed"
  });
  
  // Hide analyzer panel
  document.getElementById('lab-simulation-panel').classList.add('hidden');
  document.getElementById('lab-sim-progress').style.width = '0%';
  
  addAgentLog(`Central Lab uploaded blood work results for ${patientName}: ALT [${alt} U/L], AST [${ast} U/L], Bilirubin [${bilirubin} mg/dL].`, "success");
  showToast("Lab Panel Uploaded", `Results registered to patient's clinical file.`);
  
  // Refresh views
  renderLabDashboard();
}

// ==========================================
// 7. Dynamic SVG Chart Drawing
// ==========================================

function renderBiochemicalChart(records) {
  const container = document.getElementById('svg-chart-container');
  container.innerHTML = '';
  
  const width = container.clientWidth || 600;
  const height = 200;
  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 30;
  
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;
  
  // Find max value in records for scale (min 100 to look uniform)
  const maxVal = Math.max(...records.map(r => Math.max(r.alt, r.ast)), 100);
  
  // Create SVG element
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", "100%");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  
  // Draw grid lines
  const gridLines = 4;
  for (let i = 0; i <= gridLines; i++) {
    const yVal = Math.round((maxVal / gridLines) * i);
    const yPos = height - paddingBottom - (chartHeight / gridLines) * i;
    
    // Line
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", paddingLeft);
    line.setAttribute("y1", yPos);
    line.setAttribute("x2", width - paddingRight);
    line.setAttribute("y2", yPos);
    line.setAttribute("stroke", "rgba(255, 255, 255, 0.05)");
    line.setAttribute("stroke-width", "1");
    svg.appendChild(line);
    
    // Y Axis labels
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", paddingLeft - 8);
    text.setAttribute("y", yPos + 4);
    text.setAttribute("fill", "var(--color-text-muted)");
    text.setAttribute("font-size", "10px");
    text.setAttribute("text-anchor", "end");
    text.textContent = yVal;
    svg.appendChild(text);
  }

  // Draw X Axis dates
  const pointsCount = records.length;
  const xCoords = [];
  
  records.forEach((record, index) => {
    const xPos = paddingLeft + (chartWidth / Math.max(pointsCount - 1, 1)) * index;
    xCoords.push(xPos);
    
    // Label
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", xPos);
    text.setAttribute("y", height - 10);
    text.setAttribute("fill", "var(--color-text-muted)");
    text.setAttribute("font-size", "10px");
    text.setAttribute("text-anchor", "middle");
    text.textContent = record.date;
    svg.appendChild(text);
  });
  
  // Map values to coordinates
  const altPoints = [];
  const astPoints = [];
  
  records.forEach((record, index) => {
    const x = xCoords[index];
    const yAlt = height - paddingBottom - (record.alt / maxVal) * chartHeight;
    const yAst = height - paddingBottom - (record.ast / maxVal) * chartHeight;
    
    altPoints.push({ x, y: yAlt, val: record.alt });
    astPoints.push({ x, y: yAst, val: record.ast });
  });
  
  // Render Paths
  if (pointsCount > 1) {
    svg.appendChild(createPath(altPoints, "var(--accent-cyan)", "alt-line"));
    svg.appendChild(createPath(astPoints, "var(--accent-emerald)", "ast-line"));
  }
  
  // Render Dots
  altPoints.forEach(p => {
    svg.appendChild(createDot(p.x, p.y, "var(--accent-cyan)", `ALT: ${p.val} U/L`));
  });
  
  astPoints.forEach(p => {
    svg.appendChild(createDot(p.x, p.y, "var(--accent-emerald)", `AST: ${p.val} U/L`));
  });
  
  container.appendChild(svg);
}

function createPath(points, color, className) {
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    d += ` L ${points[i].x} ${points[i].y}`;
  }
  path.setAttribute("d", d);
  path.setAttribute("class", `chart-line ${className}`);
  path.setAttribute("stroke", color);
  return path;
}

function createDot(cx, cy, color, title) {
  const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
  
  const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  circle.setAttribute("cx", cx);
  circle.setAttribute("cy", cy);
  circle.setAttribute("r", "4");
  circle.setAttribute("fill", color);
  circle.setAttribute("stroke", "var(--bg-card)");
  circle.setAttribute("class", "chart-dot");
  
  const tooltip = document.createElementNS("http://www.w3.org/2000/svg", "title");
  tooltip.textContent = title;
  
  circle.appendChild(tooltip);
  group.appendChild(circle);
  return group;
}

// ==========================================
// 8. Utility & Helper Functions
// ==========================================

function getFormattedTime(offsetSeconds = 0) {
  const date = new Date(Date.now() - offsetSeconds * 1000);
  let hrs = date.getHours();
  let mins = date.getMinutes();
  const ampm = hrs >= 12 ? 'PM' : 'AM';
  hrs = hrs % 12;
  hrs = hrs ? hrs : 12; // 0 should be 12
  mins = mins < 10 ? '0' + mins : mins;
  return `${hrs}:${mins} ${ampm}`;
}

function addAgentLog(text, type = 'info') {
  state.agentLogs.push({
    timestamp: getFormattedTime(),
    text: text,
    type: type
  });
  
  // Cap logs to 20 items to prevent bloat
  if (state.agentLogs.length > 20) {
    state.agentLogs.shift();
  }
  
  // Refresh caregiver view if currently active
  if (state.activeRole === 'caregiver') {
    renderCaregiverDashboard(patientsData[state.currentPatient]);
  }
}

function showToast(title, message, isWarning = false) {
  const toast = document.getElementById('notification-toast');
  const titleEl = toast.querySelector('.toast-title');
  const messageEl = toast.querySelector('.toast-message');
  const iconEl = toast.querySelector('.toast-icon');
  
  titleEl.textContent = title;
  messageEl.textContent = message;
  
  if (isWarning) {
    toast.style.borderColor = 'var(--state-danger)';
    iconEl.textContent = '⚠';
    iconEl.style.color = 'var(--state-danger)';
    iconEl.style.backgroundColor = 'var(--state-danger-glow)';
  } else {
    toast.style.borderColor = 'var(--accent-emerald)';
    iconEl.textContent = '✓';
    iconEl.style.color = 'var(--accent-emerald)';
    iconEl.style.backgroundColor = 'rgba(16, 185, 129, 0.15)';
  }
  
  toast.classList.add('show');
  
  setTimeout(() => {
    toast.classList.remove('show');
  }, 4000);
}

// Redraw chart on window resize
window.addEventListener('resize', () => {
  if (state.activeRole === 'doctor') {
    renderBiochemicalChart(patientsData[state.currentPatient].biochemistry);
  }
});

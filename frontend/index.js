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
  ],
  activeSessions: {}, // Holds active Google ADK sessionId per agent app
  isChatOpen: false
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

async function syncWithBackend() {
  const patient = patientsData[state.currentPatient];
  try {
    // 1. Fetch prescription
    const prescRes = await fetch(`/api/patient/prescription?patient_id=${state.currentPatient}`);
    if (prescRes.ok) {
      const presc = await prescRes.json();
      patient.medication = presc.medication;
      patient.frequency = presc.frequency;
    }
  } catch (err) {
    console.log("Not running in backend server environment, using local mock prescription");
  }

  try {
    // 2. Fetch lab records
    const labRes = await fetch(`/api/doctor/lab-records?patient_id=${state.currentPatient}`);
    if (labRes.ok) {
      const records = await labRes.json();
      if (records && records.length > 0) {
        patient.biochemistry = records;
      }
    }
  } catch (err) {
    console.log("Not running in backend server environment, using local mock lab records");
  }

  try {
    // 3. Fetch caregiver alerts
    const alertRes = await fetch(`/api/caregiver/alerts?patient_id=${state.currentPatient}`);
    if (alertRes.ok) {
      const alerts = await alertRes.json();
      if (alerts && alerts.length > 0) {
        state.agentLogs = state.agentLogs.filter(log => log.type !== 'alert');
        alerts.forEach(alert => {
          state.agentLogs.push({
            timestamp: alert.timestamp,
            text: alert.text,
            type: alert.type
          });
        });
      }
    }
  } catch (err) {
    console.log("Not running in backend server environment, using local mock alerts");
  }

  try {
    // 4. Fetch patient health logs from MongoDB to populate live metrics dashboard counters
    const logsRes = await fetch(`/api/patient/health-logs?patient_id=${state.currentPatient}`);
    if (logsRes.ok) {
      const logs = await logsRes.json();
      if (logs && logs.length > 0) {
        patient.vitals = {};
        
        const latestSleep = logs.find(l => l.event === "sleep_quality");
        if (latestSleep) {
          patient.vitals.sleep_hours = latestSleep.data.hours_slept;
          patient.vitals.sleep_quality = latestSleep.data.quality || "good";
        }
        
        const latestProtein = logs.find(l => l.event === "protein_intake");
        if (latestProtein) {
          patient.vitals.protein_grams = latestProtein.data.protein_grams;
        }
        
        const latestWater = logs.find(l => l.event === "water_intake");
        if (latestWater) {
          patient.vitals.fluid_litres = latestWater.data.fluid_litres;
        }
        
        const latestSalt = logs.find(l => l.event === "salt_intake");
        if (latestSalt) {
          patient.vitals.salt_grams = latestSalt.data.salt_grams;
        }
        
        const latestWeight = logs.find(l => l.event === "weight");
        if (latestWeight) {
          patient.vitals.weight_kg = latestWeight.data.weight_kg;
        }
        
        const latestAmmonia = logs.find(l => l.event === "ammonia_level");
        if (latestAmmonia) {
          patient.vitals.ammonia_ppm = latestAmmonia.data.ammonia_level_ppm;
          patient.vitals.ammonia_status = latestAmmonia.data.status || "normal";
        }
        
        const latestExercise = logs.find(l => l.event === "exercise");
        if (latestExercise) {
          patient.vitals.exercise_completed = latestExercise.data.exercise_completed;
          patient.vitals.exercise_type = latestExercise.data.exercise_type || "yoga";
          patient.vitals.exercise_duration = latestExercise.data.duration_minutes || 30;
        }
      }
    }
  } catch (err) {
    console.log("Not running in backend server environment, using local mock health logs", err);
  }
}

async function openDashboard(role) {
  state.activeRole = role;
  
  // Clear any playing audio when switching views
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  
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
  
  // Sync with real backend database if available
  await syncWithBackend();
  
  // Show and configure the floating chat trigger for the current dashboard's agent
  configureFloatingChatForRole(role);
  
  // Render specific role components
  renderDashboard(role);
  showToast("Portal Connection Established", `Switched to the ${role} dashboard view.`);
}

function closeDashboard() {
  const overlay = document.getElementById('dashboard-overlay');
  overlay.classList.remove('active');
  document.body.style.overflow = 'auto'; // Unlock scroll
  
  // Clear any playing audio when exiting
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  
  // Hide chat trigger and close chat window if open
  document.getElementById('floating-chat-trigger').style.display = 'none';
  if (state.isChatOpen) {
    toggleAgentChat();
  }
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

  // Update Live Vitals Counters in DOM from MongoDB (or fallback)
  const sleepVal = patient.vitals?.sleep_hours !== undefined ? `${patient.vitals.sleep_hours}h` : "7.8h";
  const sleepSub = patient.vitals?.sleep_quality ? `Quality: ${patient.vitals.sleep_quality}` : "Quality: Good";
  document.getElementById('vital-sleep').textContent = sleepVal;
  
  const sleepSubEl = document.getElementById('vital-sleep-sub');
  if (sleepSubEl) sleepSubEl.textContent = sleepSub;

  const sleepHrs = patient.vitals?.sleep_hours !== undefined ? parseFloat(patient.vitals.sleep_hours) : 7.8;
  const sleepPercent = Math.min(sleepHrs / 8.0, 1.0);
  const sleepOffset = 106.8 * (1.0 - sleepPercent);
  const sleepCircle = document.getElementById('ring-sleep-circle');
  if (sleepCircle) sleepCircle.style.strokeDashoffset = sleepOffset;

  const proteinVal = patient.vitals?.protein_grams !== undefined ? `${patient.vitals.protein_grams}g` : "80g";
  document.getElementById('vital-protein').textContent = proteinVal;

  const proteinGrams = patient.vitals?.protein_grams !== undefined ? parseFloat(patient.vitals.protein_grams) : 80.0;
  const proteinPercent = Math.min(proteinGrams / 80.0, 1.0);
  const proteinOffset = 106.8 * (1.0 - proteinPercent);
  const proteinCircle = document.getElementById('ring-protein-circle');
  if (proteinCircle) proteinCircle.style.strokeDashoffset = proteinOffset;

  const waterVal = patient.vitals?.fluid_litres !== undefined ? `${patient.vitals.fluid_litres}L` : "2.7L";
  document.getElementById('vital-water').textContent = waterVal;

  const waterLiters = patient.vitals?.fluid_litres !== undefined ? parseFloat(patient.vitals.fluid_litres) : 2.7;
  const waterPercent = Math.min(waterLiters / 2.5, 1.0);
  const waterOffset = 106.8 * (1.0 - waterPercent);
  const waterCircle = document.getElementById('ring-water-circle');
  if (waterCircle) waterCircle.style.strokeDashoffset = waterOffset;

  const saltVal = patient.vitals?.salt_grams !== undefined ? `${patient.vitals.salt_grams}g` : "3.6g";
  const saltSub = patient.vitals?.salt_grams !== undefined ? (patient.vitals.salt_grams <= 5.0 ? "Limit: < 5.0g" : "Exceeds Limit!") : "Limit: < 5.0g";
  document.getElementById('vital-salt').textContent = saltVal;
  
  const saltSubEl = document.getElementById('vital-salt-sub');
  if (saltSubEl) saltSubEl.textContent = saltSub;

  const saltGrams = patient.vitals?.salt_grams !== undefined ? parseFloat(patient.vitals.salt_grams) : 3.6;
  const saltPercent = Math.min(saltGrams / 5.0, 1.0);
  const saltOffset = 106.8 * (1.0 - saltPercent);
  const saltCircle = document.getElementById('ring-salt-circle');
  if (saltCircle) {
    saltCircle.style.strokeDashoffset = saltOffset;
    if (saltGrams > 5.0) {
      saltCircle.style.stroke = "var(--state-danger)";
    } else {
      saltCircle.style.stroke = "#ea580c";
    }
  }

  const weightVal = patient.vitals?.weight_kg !== undefined ? `${patient.vitals.weight_kg}kg` : "78.0kg";
  document.getElementById('vital-weight').textContent = weightVal;

  const weightPercent = 1.0;
  const weightOffset = 106.8 * (1.0 - weightPercent);
  const weightCircle = document.getElementById('ring-weight-circle');
  if (weightCircle) weightCircle.style.strokeDashoffset = weightOffset;

  // Ammonia status text
  const ammoniaVal = patient.vitals?.ammonia_ppm !== undefined ? `${patient.vitals.ammonia_ppm} ppm` : "32.1 ppm";
  const ammoniaStatus = patient.vitals?.ammonia_status ? patient.vitals.ammonia_status : "Normal";
  const ammoniaEl = document.getElementById('patient-ammonia-text');
  if (ammoniaEl) {
    ammoniaEl.textContent = `${ammoniaVal} (${ammoniaStatus})`;
    if (ammoniaStatus.toLowerCase() === 'normal') {
      ammoniaEl.className = "text-success";
    } else {
      ammoniaEl.className = "text-danger animate-pulse";
    }
  }

  // Exercise status text
  const exerciseEl = document.getElementById('patient-exercise-text');
  if (exerciseEl) {
    if (patient.vitals?.exercise_completed) {
      exerciseEl.textContent = `${patient.vitals.exercise_type} (${patient.vitals.exercise_duration} mins) Completed`;
      exerciseEl.className = "text-success";
    } else {
      exerciseEl.textContent = "Awaiting exercise session";
      exerciseEl.className = "text-muted";
    }
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

  // Load and render chronological health logs history from MongoDB
  fetchAndRenderHealthLogsTable();
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

async function logSymptom(event) {
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
  
  // Save to database if running through backend
  try {
    await fetch("/api/patient/symptoms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patient_name: state.currentPatient,
        fatigue: fatigue,
        nausea: nausea,
        jaundice: jaundice
      })
    });
  } catch (err) {
    console.log("Could not save symptom to backend DB");
  }

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

async function applyPrescriptionChange() {
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
  
  // Save to database if running through backend
  try {
    await fetch("/api/doctor/prescription", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patient_name: state.currentPatient,
        medication: med,
        frequency: freq
      })
    });
  } catch (err) {
    console.log("Could not save prescription to backend DB");
  }

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

// ==========================================
// 9. Real-Time Conversational AI Agent Chat
// ==========================================

function toggleStoryGuide() {
  const content = document.getElementById('story-steps-content');
  const chevron = document.getElementById('story-chevron');
  content.classList.toggle('collapsed');
  
  if (content.classList.contains('collapsed')) {
    chevron.style.transform = 'rotate(-90deg)';
  } else {
    chevron.style.transform = 'rotate(0deg)';
  }
}

async function triggerStoryStep(stepNum) {
  const inputEl = document.getElementById('chat-user-input');
  
  if (stepNum === 1) {
    // Switch to patient portal if not already there
    if (state.activeRole !== 'patient') {
      openDashboard('patient');
    }
    inputEl.value = "Hi Lila, I'm John. I need to check in today. I am feeling extremely tired, fatigue level is 9 out of 10. And my wife noticed that my eyes are looking slightly yellow.";
  } else if (stepNum === 2) {
    // Switch to caregiver hub
    if (state.activeRole !== 'caregiver') {
      openDashboard('caregiver');
    }
    inputEl.value = "I am John's caregiver. Lila logged a jaundice alert for John today. Can you fetch my daily summaries and give me a full briefing on his status and advice?";
  } else if (stepNum === 3) {
    // Switch to doctor panel
    if (state.activeRole !== 'doctor') {
      openDashboard('doctor');
    }
    inputEl.value = "I am Dr. Elizabeth Vance. Can you pull the comprehensive profile for patient John Doe, calculate his transplant MELD-Na score, and provide evidence-based clinical recommendations?";
  }
  
  // Submit the form automatically to trigger the Orchestrator
  const form = document.querySelector('.chat-input-area');
  const event = new Event('submit', { cancelable: true });
  form.dispatchEvent(event);
}

const ORCHESTRATOR_MAPPING = {
  app_name: "orchestrator",
  title: "LiverLink Orchestrator",
  welcome: "Hello! I am the central LiverLink Orchestrator agent. I coordinate patient check-ins with Lila, caregiver summaries with Aria, biochemistry Extractions, and Hepatology Specialist pathways for doctors. How can I help you today?"
};

function configureFloatingChatForRole(role) {
  const trigger = document.getElementById('floating-chat-trigger');
  trigger.style.display = 'flex';
  
  // Clean and reset messages for a fresh portal session if not yet spoken
  const msgContainer = document.getElementById('chat-messages-container');
  if (msgContainer.children.length <= 1) {
    msgContainer.innerHTML = `
      <div class="chat-bubble system">
        <strong>System Connected</strong>
        <p id="chat-system-welcome">Connected to Global Orchestrator Agent. Ask any care check-in questions, caregiver audits, or physician metrics.</p>
      </div>
    `;
  }
}

function toggleAgentChat() {
  const sidebar = document.getElementById('agent-chat-sidebar');
  state.isChatOpen = !state.isChatOpen;
  
  if (state.isChatOpen) {
    sidebar.classList.add('active');
  } else {
    sidebar.classList.remove('active');
  }
}

async function sendAgentChatMessage(event) {
  if (event) event.preventDefault();
  
  const inputEl = document.getElementById('chat-user-input');
  const userText = inputEl.value.trim();
  if (!userText) return;
  
  // Disable form input during call
  inputEl.value = '';
  inputEl.disabled = true;
  const submitBtn = document.getElementById('chat-submit-btn');
  submitBtn.disabled = true;
  
  // Append user bubble to UI
  appendChatBubble("user", "You", userText);
  
  try {
    const appName = ORCHESTRATOR_MAPPING.app_name;
    
    // 1. Establish session if not cached
    if (!state.activeSessions[appName]) {
      const sessionId = `session-${appName}-${Date.now()}`;
      state.activeSessions[appName] = sessionId;
      
      // Initialize ADK session
      await fetch(`/apps/${appName}/users/liverlink-user/sessions/${sessionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
    }
    
    const activeSessionId = state.activeSessions[appName];
    
    // 2. Dispatch query to ADK /run
    const body = {
      app_name: appName,
      user_id: "liverlink-user",
      session_id: activeSessionId,
      new_message: {
        role: "user",
        parts: [
          { text: userText }
        ]
      }
    };
    
    const res = await fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    
    const events = await res.json();
    
    // 3. Assemble agent response text
    let responseText = "";
    
    // Check for orchestrator response blocks
    for (const e of events) {
      if (e.author === "liverlink_orchestrator" && e.content?.parts) {
        responseText += e.content.parts.map(p => p.text || '').join('');
      }
    }
    
    // If not found, look for delegate responses (e.g. Lila, Aria, etc. or ADK's default fallback)
    if (!responseText.trim()) {
      for (const e of events) {
        if (e.author !== 'user' && e.content?.parts) {
          responseText += e.content.parts.map(p => p.text || '').join('');
        }
      }
    }
    
    if (!responseText.trim()) {
      responseText = "Update recognized. The telemetry logs have been updated.";
    }
    
    // Append orchestrator bubble to UI
    appendChatBubble("agent", ORCHESTRATOR_MAPPING.title, responseText);
    
    // Voice read aloud (speaks with a calm, peaceful therapeutic voice)
    speakWithCalmVoice(responseText);
    
    // Refresh dashboard values in case database is modified during check-ins
    await syncWithBackend();
    renderDashboard(state.activeRole);
    
  } catch (err) {
    console.error("Orchestrator query failed:", err);
    appendChatBubble("system", "Network Error", "The AI orchestrator server is offline. Run ./run_all.sh to launch.");
  } finally {
    inputEl.disabled = false;
    submitBtn.disabled = false;
    inputEl.focus();
  }
}

function appendChatBubble(sender, authorLabel, text) {
  const container = document.getElementById('chat-messages-container');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${sender}`;
  
  // Extract custom [VIDEO_EMBED:url] tag if present
  let cleanText = text;
  let videoEmbedHtml = '';
  
  const videoMatch = text.match(/\[VIDEO_EMBED:([^\]]+)\]/);
  if (videoMatch) {
    const embedUrl = videoMatch[1].trim();
    cleanText = text.replace(/\[VIDEO_EMBED:[^\]]+\]/, '');
    videoEmbedHtml = `
      <div class="video-container" style="margin-top: 12px; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0 4px 15px rgba(0,0,0,0.3); background-color: #000; width: 100%;">
        <iframe width="100%" height="180" src="${embedUrl}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen style="display: block;"></iframe>
      </div>
    `;
  }
  
  bubble.innerHTML = `
    <strong>${authorLabel}</strong>
    <p>${cleanText}</p>
    ${videoEmbedHtml}
  `;
  
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// ==============================================================================
// 10. Live MongoDB Health Logging Timeline & Advanced App Handlers
// ==============================================================================

async function fetchAndRenderHealthLogsTable() {
  const tbody = document.getElementById('patient-logs-timeline-tbody');
  if (!tbody) return;
  
  try {
    const res = await fetch(`/api/patient/health-logs?patient_id=${state.currentPatient}`);
    if (!res.ok) throw new Error("API health-logs fetch error");
    
    const logs = await res.json();
    tbody.innerHTML = '';
    
    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-muted" style="text-align: center; padding: 20px;">No health logs found in MongoDB for this patient. Start a chat or run a scan!</td></tr>`;
      return;
    }
    
    // Display up to 15 latest records for John
    logs.slice(0, 15).forEach(log => {
      const tr = document.createElement('tr');
      
      // Format Date/Time beautifully
      let dateStr = log.date;
      if (log.timestamp) {
        try {
          const dt = new Date(log.timestamp);
          dateStr = `${dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} at ${dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        } catch (e) {}
      }
      
      // Format Parameter Type with pretty icons
      let paramLabel = log.event;
      let emoji = "📝";
      if (log.event === "medication_adherence") { paramLabel = "Medication Adherence"; emoji = "💊"; }
      else if (log.event === "sleep_quality") { paramLabel = "Sleep Quality"; emoji = "🌙"; }
      else if (log.event === "protein_intake") { paramLabel = "Protein Intake"; emoji = "🥚"; }
      else if (log.event === "water_intake") { paramLabel = "Water / Hydration"; emoji = "💧"; }
      else if (log.event === "salt_intake") { paramLabel = "Salt / Sodium Intake"; emoji = "🧂"; }
      else if (log.event === "mood_and_symptoms") { paramLabel = "Mood & Symptoms"; emoji = "💭"; }
      else if (log.event === "fatigue") { paramLabel = "Fatigue Level"; emoji = "🥱"; }
      else if (log.event === "appetite") { paramLabel = "Appetite Status"; emoji = "🥣"; }
      else if (log.event === "weight") { paramLabel = "Body Weight"; emoji = "⚖️"; }
      else if (log.event === "ammonia_level") { paramLabel = "Blood Ammonia level"; emoji = "🤲"; }
      else if (log.event === "exercise") { paramLabel = "Exercise Workout"; emoji = "🏃‍♂️"; }
      else if (log.event === "lab_report") { paramLabel = "Biochemistry Lab Report"; emoji = "🔬"; }
      
      // Format clinical details
      let valText = "";
      const d = log.data || {};
      if (log.event === "medication_adherence") {
        valText = d.medications_taken ? "All prescribed doses taken" : "Missed medications";
        if (d.notes) valText += ` — ${d.notes}`;
      } else if (log.event === "sleep_quality") {
        valText = `${d.hours_slept} hours slept (Quality: ${d.quality || 'fair'})`;
      } else if (log.event === "protein_intake") {
        valText = `${d.protein_grams} grams consumed`;
        if (d.sources && d.sources.length) valText += ` [Sources: ${d.sources.join(', ')}]`;
      } else if (log.event === "water_intake") {
        valText = `${d.fluid_litres} Liters consumed`;
      } else if (log.event === "salt_intake") {
        valText = `${d.salt_grams}g table salt (Limit: ${d.within_recommended_limit ? 'OK' : 'EXCEEDED'})`;
      } else if (log.event === "mood_and_symptoms") {
        valText = `Mood: ${d.mood || 'stable'}`;
        if (d.fatigue_level_str) valText += `, Fatigue: ${d.fatigue_level_str}, Jaundice: ${d.jaundice_str || 'No'}`;
      } else if (log.event === "fatigue") {
        valText = `Fatigue Level: ${d.fatigue_level}/10`;
      } else if (log.event === "appetite") {
        valText = `Appetite: ${d.appetite_level}/10. Eaten: ${d.food_consumed || 'not logged'}`;
      } else if (log.event === "weight") {
        valText = `${d.weight_kg} kg`;
        if (d.weight_change_kg) valText += ` (${d.weight_change_kg > 0 ? '+' : ''}${d.weight_change_kg} kg change)`;
      } else if (log.event === "ammonia_level") {
        valText = `Blood Ammonia: ${d.ammonia_level_ppm} µmol/L (Status: ${d.status || 'normal'})`;
      } else if (log.event === "exercise") {
        valText = `Completed ${d.duration_minutes || 20} mins of ${d.exercise_type || 'restorative yoga'}`;
      } else if (log.event === "lab_report") {
        valText = `Urgency: ${d.urgency_level || 'LOW'}. ALT: ${d.test_results?.find(r=>r.name.includes("ALT"))?.value || 'N/A'} U/L`;
      } else {
        valText = JSON.stringify(d);
      }
      
      // Determine badge alarms
      let badgeClass = "badge-success";
      let badgeLabel = "NORMAL";
      
      if (log.flags && log.flags.length > 0) {
        badgeClass = "badge-danger animate-pulse";
        badgeLabel = log.flags.join(', ');
      } else if (log.event === "salt_intake" && !d.within_recommended_limit) {
        badgeClass = "badge-warning";
        badgeLabel = "EXCEEDS LIMIT";
      } else if (log.event === "ammonia_level" && d.status === "elevated") {
        badgeClass = "badge-danger animate-pulse";
        badgeLabel = "HIGH AMMONIA";
      } else if (log.event === "medication_adherence" && !d.medications_taken) {
        badgeClass = "badge-danger";
        badgeLabel = "MISSED DOSES";
      }
      
      tr.innerHTML = `
        <td style="font-weight: 500;">${dateStr}</td>
        <td><span style="font-size: 14px; margin-right: 6px;">${emoji}</span> <strong>${paramLabel}</strong></td>
        <td style="color: var(--color-text-secondary); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${valText}</td>
        <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
      `;
      tbody.appendChild(tr);
    });
    
    // Draw visual trend graphics for Sleep (Line chart) and Water (Bar chart) from MongoDB history
    drawWeeklyVitalsTrendCharts(logs);
    
  } catch (err) {
    console.error("Error loading timelines:", err);
    tbody.innerHTML = `<tr><td colspan="4" class="text-danger" style="text-align: center; padding: 20px;">Failed to load logs from database. Run ./run_all.sh to launch API.</td></tr>`;
  }
}

// Helper to draw weekly patient trend charts dynamically using SVG
function drawWeeklyVitalsTrendCharts(logs) {
  // 1. Gather distinct days of logs (last 5 days)
  const sleepLogs = logs.filter(l => l.event === "sleep_quality").reverse();
  const waterLogs = logs.filter(l => l.event === "water_intake").reverse();
  
  // Clean logs to keep only the latest one per day if multiples exist
  const getLatestPerDay = (items, key) => {
    const map = {};
    items.forEach(i => { map[i.date] = i.data[key]; });
    return Object.keys(map).sort().slice(-5).map(date => ({ date, value: parseFloat(map[date]) }));
  };
  
  const weeklySleep = getLatestPerDay(sleepLogs, "hours_slept");
  const weeklyWater = getLatestPerDay(waterLogs, "fluid_litres");
  
  // 2. Render Sleep Line Chart
  renderSleepLineChart(weeklySleep);
  
  // 3. Render Water Bar Chart
  renderWaterBarChart(weeklyWater);
}

function renderSleepLineChart(data) {
  const container = document.getElementById('patient-sleep-svg-chart');
  if (!container) return;
  container.innerHTML = '';
  
  // If no data, fill with standard 5-day dummy data so it's always beautiful
  if (data.length === 0) {
    data = [
      { date: "June 09", value: 7.2 },
      { date: "June 10", value: 6.8 },
      { date: "June 11", value: 8.0 },
      { date: "June 12", value: 7.5 },
      { date: "June 13", value: 7.8 }
    ];
  }
  
  // Standardized fixed-size coordinate system for bulletproof responsiveness via viewBox!
  const width = 500;
  const height = 140;
  const paddingLeft = 30;
  const paddingRight = 30;
  const paddingTop = 20;
  const paddingBottom = 20;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;
  
  const maxVal = 10; // Max sleep scale
  const pointsCount = data.length;
  
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", "100%");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  
  // Grid lines
  for (let i = 0; i <= 4; i++) {
    const yVal = Math.round((maxVal / 4) * i);
    const yPos = height - paddingBottom - (chartHeight / 4) * i;
    
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", paddingLeft);
    line.setAttribute("y1", yPos);
    line.setAttribute("x2", width - paddingRight);
    line.setAttribute("y2", yPos);
    line.setAttribute("stroke", "rgba(255,255,255,0.06)");
    svg.appendChild(line);
  }
  
  // Map points
  const points = data.map((d, index) => {
    const x = paddingLeft + (chartWidth / Math.max(pointsCount - 1, 1)) * index;
    const y = height - paddingBottom - (d.value / maxVal) * chartHeight;
    return { x, y, val: d.value, date: d.date };
  });
  
  // Draw path
  if (points.length > 1) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    let d = `M ${points[0].x} ${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      d += ` L ${points[i].x} ${points[i].y}`;
    }
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "var(--accent-cyan)");
    path.setAttribute("stroke-width", "3");
    path.setAttribute("stroke-linecap", "round");
    svg.appendChild(path);
  }
  
  // Draw points & labels
  points.forEach(p => {
    // Circle
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", p.x);
    circle.setAttribute("cy", p.y);
    circle.setAttribute("r", "5");
    circle.setAttribute("fill", "var(--accent-cyan)");
    circle.setAttribute("stroke", "var(--bg-secondary)");
    circle.setAttribute("stroke-width", "2");
    
    const tooltip = document.createElementNS("http://www.w3.org/2000/svg", "title");
    tooltip.textContent = `${p.val} hrs on ${p.date}`;
    circle.appendChild(tooltip);
    svg.appendChild(circle);
    
    // Value text
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", p.x);
    text.setAttribute("y", p.y - 10);
    text.setAttribute("fill", "#fff");
    text.setAttribute("font-size", "10px");
    text.setAttribute("font-weight", "600");
    text.setAttribute("text-anchor", "middle");
    text.textContent = `${p.val}h`;
    svg.appendChild(text);
    
    // Date label
    const dateText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    dateText.setAttribute("x", p.x);
    dateText.setAttribute("y", height - 4);
    dateText.setAttribute("fill", "var(--color-text-secondary)");
    dateText.setAttribute("font-size", "10px");
    dateText.setAttribute("text-anchor", "middle");
    
    let label = p.date;
    if (p.date.includes("-")) {
      const parts = p.date.split("-");
      label = parts[2] ? parts[2] : parts[1]; // Just show the day number
    }
    dateText.textContent = label;
    svg.appendChild(dateText);
  });
  
  container.appendChild(svg);
}

function renderWaterBarChart(data) {
  const container = document.getElementById('patient-water-svg-chart');
  if (!container) return;
  container.innerHTML = '';
  
  if (data.length === 0) {
    data = [
      { date: "June 09", value: 2.4 },
      { date: "June 10", value: 2.5 },
      { date: "June 11", value: 2.8 },
      { date: "June 12", value: 2.6 },
      { date: "June 13", value: 2.7 }
    ];
  }
  
  // Standardized fixed-size coordinate system for bulletproof responsiveness via viewBox!
  const width = 500;
  const height = 140;
  const paddingLeft = 30;
  const paddingRight = 30;
  const paddingTop = 20;
  const paddingBottom = 20;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;
  
  const maxVal = 4.0; // Max water intake scale
  const pointsCount = data.length;
  const barWidth = 32; // Comfortable uniform bar width
  
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", "100%");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  
  // Grid lines
  for (let i = 0; i <= 4; i++) {
    const yPos = height - paddingBottom - (chartHeight / 4) * i;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", paddingLeft);
    line.setAttribute("y1", yPos);
    line.setAttribute("x2", width - paddingRight);
    line.setAttribute("y2", yPos);
    line.setAttribute("stroke", "rgba(255,255,255,0.06)");
    svg.appendChild(line);
  }
  
  // Draw Bars
  data.forEach((d, index) => {
    const colWidth = chartWidth / pointsCount;
    const x = paddingLeft + colWidth * index + (colWidth - barWidth) / 2;
    const barHeight = (d.value / maxVal) * chartHeight;
    const y = height - paddingBottom - barHeight;
    
    // Bar rect
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", x);
    rect.setAttribute("y", y);
    rect.setAttribute("width", barWidth);
    rect.setAttribute("height", barHeight);
    rect.setAttribute("fill", "url(#water-grad)");
    rect.setAttribute("rx", "4");
    
    const tooltip = document.createElementNS("http://www.w3.org/2000/svg", "title");
    tooltip.textContent = `${d.value} Liters on ${d.date}`;
    rect.appendChild(tooltip);
    svg.appendChild(rect);
    
    // Gradients definitions
    if (index === 0) {
      const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      defs.innerHTML = `
        <linearGradient id="water-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#60a5fa" />
          <stop offset="100%" stop-color="#2563eb" />
        </linearGradient>
      `;
      svg.appendChild(defs);
    }
    
    // Value text
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", x + (barWidth / 2));
    text.setAttribute("y", y - 8);
    text.setAttribute("fill", "#fff");
    text.setAttribute("font-size", "10px");
    text.setAttribute("font-weight", "600");
    text.setAttribute("text-anchor", "middle");
    text.textContent = `${d.value}L`;
    svg.appendChild(text);
    
    // Date label
    const dateText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    dateText.setAttribute("x", x + (barWidth / 2));
    dateText.setAttribute("y", height - 4);
    dateText.setAttribute("fill", "var(--color-text-secondary)");
    dateText.setAttribute("font-size", "10px");
    dateText.setAttribute("text-anchor", "middle");
    
    let label = d.date;
    if (d.date.includes("-")) {
      const parts = d.date.split("-");
      label = parts[2] ? parts[2] : parts[1];
    }
    dateText.textContent = label;
    svg.appendChild(dateText);
  });
  
  container.appendChild(svg);
}

function launchAmmoniaScanner() {
  const panel = document.getElementById('hand-ai-scanner-section');
  if (!panel) return;
  
  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth' });
  
  const progressBar = document.getElementById('scanner-progress');
  const statusText = document.getElementById('scanner-status-text');
  progressBar.style.width = '0%';
  statusText.textContent = "Connecting to device camera stream...";
  
  let progress = 0;
  const interval = setInterval(async () => {
    progress += 2;
    progressBar.style.width = `${progress}%`;
    
    if (progress === 15) {
      statusText.textContent = "Aligning hand silhouette guide...";
    } else if (progress === 40) {
      statusText.textContent = "Tracking finger micro-tremors (neurological baseline)...";
    } else if (progress === 70) {
      statusText.textContent = "Analyzing ocular eye tracking & visual-motor delay...";
    } else if (progress >= 100) {
      clearInterval(interval);
      statusText.textContent = "Processing visual telemetry logs...";
      
      setTimeout(async () => {
        statusText.textContent = "Scan complete! Ammonia: 32.1 µmol/L (Safe/Normal)";
        showToast("Hand AI Scan Complete", "Ammonia level: 32.1 µmol/L recorded to MongoDB.");
        
        // Save the result directly to MongoDB health logs!
        try {
          await fetch("/api/patient/health-logs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              patient_name: state.currentPatient,
              event: "ammonia_level",
              data: {
                ammonia_level_ppm: 32.1,
                status: "normal",
                notes: "Hand AI visual ocular & micro-tremor scan."
              }
            })
          });
        } catch (e) {
          console.log("DB sync offline, simulated local update instead.");
        }
        
        // Add activity log for caregiver
        addAgentLog(`Patient completed blood ammonia level check via Hand AI App: 32.1 µmol/L (Normal).`, 'success');
        
        // Refresh patient view & timeline
        await syncWithBackend();
        renderDashboard(state.activeRole);
      }, 500);
    }
  }, 60);
}

function closeAmmoniaScanner() {
  const panel = document.getElementById('hand-ai-scanner-section');
  if (panel) panel.classList.add('hidden');
}

function launchExerciseTrainer() {
  // 1. Open the Chat sidebar if not active
  if (!state.isChatOpen) {
    toggleAgentChat();
  }
  
  // 2. Pre-fill chat message and send to Exercise Coach Jax
  const inputEl = document.getElementById('chat-user-input');
  if (inputEl) {
    inputEl.value = "Hi Coach Jax, I am John. I would like to do some exercise today. Please guide me through a safe routine and log it!";
    
    // Auto submit
    const form = document.querySelector('.chat-input-area');
    const event = new Event('submit', { cancelable: true });
    form.dispatchEvent(event);
    showToast("Opening Fitness App", "Connecting to Exercise Agent Coach Jax...");
  }
}

// ==============================================================================
// 11. Calm Voice Coaching Synthesis & Web Speech APIs
// ==============================================================================

// Global Voice Coaching state (ON by default for exercises)
let isCalmVoiceEnabled = true;
let activeUtterance = null;

function toggleCalmVoice() {
  isCalmVoiceEnabled = !isCalmVoiceEnabled;
  const btn = document.getElementById('btn-toggle-voice');
  const icon = document.getElementById('voice-toggle-icon');
  
  if (isCalmVoiceEnabled) {
    btn.classList.add('active');
    btn.innerHTML = `<span id="voice-toggle-icon">🔊</span> Voice On`;
    showToast("Audio Guide Active", "Coach Jax will now guide your exercise session with a calm voice.");
  } else {
    btn.classList.remove('active');
    btn.innerHTML = `<span id="voice-toggle-icon">🔇</span> Muted`;
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    showToast("Audio Guide Muted", "Conversational audio synthesis disabled.");
  }
}

function speakWithCalmVoice(text) {
  if (!isCalmVoiceEnabled || !window.speechSynthesis) return;
  
  // Clear any active playing speeches
  window.speechSynthesis.cancel();
  
  // Strip special bracketed tags like video tags before reading
  const cleanTextForSpeech = text.replace(/\[VIDEO_EMBED:[^\]]+\]/g, '').trim();
  if (!cleanTextForSpeech) return;
  
  // Create Speech synthesis Utterance
  const utterance = new SpeechSynthesisUtterance(cleanTextForSpeech);
  activeUtterance = utterance;
  
  // Custom calm, therapeutic clinical audio profile
  utterance.rate = 0.74; // Extremely calm, slower, peaceful speaking tempo
  utterance.pitch = 0.82; // Lower, warmer, deeply soothing vocal pitch (removes digital sharpness)
  utterance.volume = 0.45; // Soften the volume to 45% for a very gentle, quiet, and comforting clinical whisper
  
  // Dynamically select Samantha's high-fidelity soothing voice primarily
  const voices = window.speechSynthesis.getVoices();
  const preferredVoice = voices.find(v => 
    v.lang.includes('en') && v.name.toLowerCase().includes('samantha')
  ) || voices.find(v => 
    v.lang.includes('en') && v.name.toLowerCase().includes('siri')
  ) || voices.find(v => 
    v.lang.includes('en') && v.name.toLowerCase().includes('google') && v.name.toLowerCase().includes('us english')
  ) || voices.find(v => 
    v.lang.includes('en') && v.name.toLowerCase().includes('google')
  ) || voices.find(v => 
    v.lang.includes('en') && v.name.toLowerCase().includes('natural')
  ) || voices.find(v => v.lang.includes('en'));
  
  if (preferredVoice) {
    utterance.voice = preferredVoice;
    console.log(`[LIVERLINK VOICE] Activating Samantha / Premium voice profile: ${preferredVoice.name}`);
  }
  
  // When Coach Jax starts speaking, show active wave indicators on the active chat bubble
  utterance.onstart = () => {
    addVoiceWaveIndicator();
  };
  
  utterance.onend = () => {
    removeVoiceWaveIndicator();
  };
  
  utterance.onerror = () => {
    removeVoiceWaveIndicator();
  };
  
  window.speechSynthesis.speak(utterance);
}

function addVoiceWaveIndicator() {
  const container = document.getElementById('chat-messages-container');
  const lastAgentBubble = container.querySelector('.chat-bubble.agent:last-child');
  if (lastAgentBubble && !lastAgentBubble.querySelector('.voice-wave-container')) {
    const wave = document.createElement('div');
    wave.className = 'voice-wave-container';
    wave.innerHTML = `
      <span class="voice-bar"></span>
      <span class="voice-bar"></span>
      <span class="voice-bar"></span>
      <span class="voice-bar"></span>
    `;
    const label = lastAgentBubble.querySelector('strong');
    if (label) {
      label.appendChild(wave);
    }
  }
}

function removeVoiceWaveIndicator() {
  const container = document.getElementById('chat-messages-container');
  const waves = container.querySelectorAll('.voice-wave-container');
  waves.forEach(w => w.remove());
}

// Make sure voices are initialized and pre-cached asynchronously for Chrome/Safari
if (window.speechSynthesis) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => {
    const loadedVoices = window.speechSynthesis.getVoices();
    const samVoice = loadedVoices.find(v => 
      v.lang.includes('en') && v.name.toLowerCase().includes('samantha')
    ) || loadedVoices.find(v => 
      v.lang.includes('en') && v.name.toLowerCase().includes('siri')
    );
    if (samVoice) {
      console.log(`[LIVERLINK VOICE] Samantha vocal profile '${samVoice.name}' registered & ready.`);
    }
  };
}

// ──────────────────────────────────────────────────────────────────────────────
//  Voice Input (Speech-to-Text) using Web Speech Recognition API
// ──────────────────────────────────────────────────────────────────────────────
let speechRecognizer = null;
let isRecordingInput = false;

function toggleVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    showToast("Voice Input Unsupported", "This browser doesn't support live speech recognition. Try Google Chrome or Safari.", true);
    return;
  }
  
  const micBtn = document.getElementById('chat-mic-btn');
  const inputEl = document.getElementById('chat-user-input');
  
  if (isRecordingInput) {
    // Stop recording
    if (speechRecognizer) {
      speechRecognizer.stop();
    }
    return;
  }
  
  // Start recording
  try {
    isRecordingInput = true;
    micBtn.classList.add('recording');
    micBtn.textContent = '🛑';
    inputEl.placeholder = "Listening to your voice... Speak now!";
    
    // Stop any active playing speeches when the user starts speaking so they don't overlap
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = false;
    speechRecognizer.lang = 'en-US';
    
    speechRecognizer.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (transcript && transcript.trim()) {
        inputEl.value = transcript;
        showToast("Voice Capture", "Transcribed successfully! Press enter or send.");
        
        // Auto-submit the voice captured text for a completely hands-free voice experience!
        setTimeout(() => {
          const form = document.querySelector('.chat-input-area');
          if (form) {
            const submitEvent = new Event('submit', { cancelable: true });
            form.dispatchEvent(submitEvent);
          }
        }, 800);
      }
    };
    
    speechRecognizer.onerror = (err) => {
      console.error("Speech Recognition Error:", err);
      showToast("Voice Capture Error", "Could not catch your voice. Please check microphone permissions.", true);
      resetVoiceInputState();
    };
    
    speechRecognizer.onend = () => {
      resetVoiceInputState();
    };
    
    speechRecognizer.start();
  } catch (e) {
    console.error("Failed to start Speech Recognition:", e);
    resetVoiceInputState();
  }
}

function resetVoiceInputState() {
  isRecordingInput = false;
  const micBtn = document.getElementById('chat-mic-btn');
  const inputEl = document.getElementById('chat-user-input');
  if (micBtn) {
    micBtn.classList.remove('recording');
    micBtn.textContent = '🎤';
  }
  if (inputEl) {
    inputEl.placeholder = "Ask agent a question...";
  }
}

// ──────────────────────────────────────────────────────────────────────────────
//  Multi-Agent Care Flow router (Activates Portal & Pre-triggers chat agents)
// ──────────────────────────────────────────────────────────────────────────────
async function openAgentDashboard(agentKey) {
  if (agentKey === 'lila') {
    // Open patient portal
    await openDashboard('patient');
    // Pre-open chatbot and speak to Lila
    if (!state.isChatOpen) toggleAgentChat();
    const inputEl = document.getElementById('chat-user-input');
    if (inputEl) {
      inputEl.value = "Hi Lila! I am John. I would like to do my daily health check-in.";
      setTimeout(() => {
        const form = document.querySelector('.chat-input-area');
        if (form) form.dispatchEvent(new Event('submit'));
      }, 500);
    }
  } else if (agentKey === 'jax') {
    // Open patient portal
    await openDashboard('patient');
    // Start workout with Coach Jax
    setTimeout(() => {
      launchExerciseTrainer();
    }, 400);
  } else if (agentKey === 'aria') {
    // Open caregiver portal
    await openDashboard('caregiver');
    // Pre-open chatbot and speak to Aria
    if (!state.isChatOpen) toggleAgentChat();
    const inputEl = document.getElementById('chat-user-input');
    if (inputEl) {
      inputEl.value = "Hello Aria! Can you provide me with John's latest daily compliance summary and list any unacknowledged flags?";
      setTimeout(() => {
        const form = document.querySelector('.chat-input-area');
        if (form) form.dispatchEvent(new Event('submit'));
      }, 500);
    }
  } else if (agentKey === 'specialist') {
    // Open doctor panel
    await openDashboard('doctor');
    // Pre-open chatbot and ask the specialist decision agent
    if (!state.isChatOpen) toggleAgentChat();
    const inputEl = document.getElementById('chat-user-input');
    if (inputEl) {
      inputEl.value = "Hepatology Specialist: Pull the clinical pathway and calculate transplant indicators for John Doe.";
      setTimeout(() => {
        const form = document.querySelector('.chat-input-area');
        if (form) form.dispatchEvent(new Event('submit'));
      }, 500);
    }
  } else if (agentKey === 'lab') {
    // Open lab gateway
    await openDashboard('lab');
  }
}

// ──────────────────────────────────────────────────────────────────────────────
//  Simulate Patient Log Emergency (Orchestration Flow Trigger)
// ──────────────────────────────────────────────────────────────────────────────
async function toggleSimulatedEmergency() {
  const btn = document.getElementById('btn-simulate-emergency');
  showToast("Simulating Emergency", "Flagging jaundice & severe symptoms to MongoDB logs...", true);
  
  // 1. Set patient symptoms in local state
  const patient = patientsData["John Doe"];
  patient.symptoms.fatigue = "Severe";
  patient.symptoms.nausea = "Severe";
  patient.symptoms.jaundice = "Yes";
  
  // 2. Commit the critical check-in parameters directly into MongoDB health_logs
  // This automatically fires an URGENT Caregiver Alert in our database!
  try {
    await fetch("/api/patient/symptoms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patient_name: "John Doe",
        fatigue: "Severe",
        nausea: "Severe",
        jaundice: "Yes"
      })
    });
  } catch (e) {
    console.log("DB offline, simulating local alert trigger");
  }
  
  // 3. Append Caregiver Log indicating Orchestrator has caught the emergency
  addAgentLog("[ORCHESTRATOR INTERCEPT] CRITICAL WARNING: Jaundice & Severe Encephalopathy risks flagged from John Doe's logs. Initiating escalation flow...", 'alert');
  
  // 4. Open chat drawer and let Orchestrator handle the multi-agent routing
  setTimeout(() => {
    if (!state.isChatOpen) {
      toggleAgentChat();
    }
    const inputEl = document.getElementById('chat-user-input');
    if (inputEl) {
      inputEl.value = "Orchestrator: John's MongoDB logs have flagged an urgent jaundice & encephalopathy risk alert! Can you coordinate with Aria (caregiver) and recommend clinical steps for Dr. Elizabeth Vance?";
      // Auto-submit the emergency query to the Orchestrator
      const form = document.querySelector('.chat-input-area');
      if (form) {
        form.dispatchEvent(new Event('submit'));
      }
    }
  }, 1200);
}







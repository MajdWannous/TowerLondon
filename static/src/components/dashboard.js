/** @odoo-module **/
import { registry } from '@web/core/registry';
const { Component, useState, onWillStart, onMounted, useRef } = owl;
import { useService } from "@web/core/utils/hooks";

export class TowerDashboard extends Component {
  static template = "tower_london.TowerDashboard";

  setup() {
    this.orm = useService("orm");
    this.chartRef = useRef("chartRef");

    this.state = useState({
      patients: [],
      filteredPatients: [],
      searchTerm: "",
      selectedPatient: null,
      data: {},
      stats: {
        total_patients: 0,
        total_invoices: 0,
        improved_tests: 0,
        regressed_tests: 0,
      },
    });

    onWillStart(async () => {
      const result = await this.orm.call("tower.of.london", "get_dashboard_data", []);
      this.state.data = result.patients_data;
      this.state.stats = result.stats;
      this.state.patients = Object.keys(result.patients_data).sort((a, b) => a.localeCompare(b));
      this.state.filteredPatients = this.state.patients;
      if (this.state.patients.length > 0) {
      this.state.selectedPatient = this.state.patients[0];
      }
    });

    onMounted(() => {
      this.renderChart();
    });
  }

  renderChart() {
    const patient = this.state.selectedPatient;
    const patientData = this.state.data[patient];

    if (!patientData || !patientData.ages.length) {
      return;
    }

    const canvasEl = this.chartRef && this.chartRef.el;
    if (!canvasEl) {
      return;
    }

    const ctx = canvasEl.getContext("2d");
    if (this.chartInstance) {
      this.chartInstance.destroy();
    }

    this.chartInstance = new window.Chart(ctx, {
      type: "line",
      data: {
        labels: patientData.ages,
        datasets: [
          {
            label: "Z-Attempts",
            data: patientData.z_attempts,
            borderColor: "blue",
            fill: false,
          },
          {
            label: "Z-Time",
            data: patientData.z_time,
            borderColor: "red",
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' },
          title: {
            display: true,
            text: `Z-Scores for ${patient}`,
          },
        },
      },
    });
  }

  selectPatientFromDropdown(ev) {
    const selected = ev.target.value;
    this.state.selectedPatient = selected;
    this.renderChart();
  }
  filterPatients(ev) {
  const term = ev.target.value.toLowerCase();
  this.state.searchTerm = term;
  this.state.filteredPatients = this.state.patients.filter(p =>
    p.toLowerCase().includes(term)
  );
  if (this.state.filteredPatients.length > 0) {
    this.state.selectedPatient = this.state.filteredPatients[0];
    this.renderChart();
  }
}
printClinicReport() {

  window.open('/web#action=tower_london.action_report_clinic_dashboard', '_blank');
}
}

const actionRegistry = registry.category("actions");
actionRegistry.add("tower_london.dashboard", TowerDashboard);
export default TowerDashboard;

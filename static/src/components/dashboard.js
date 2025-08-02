/** @odoo-module **/
import { registry } from '@web/core/registry';
const {Component, useState, onWillStart, onMounted, useRef} = owl;
import { useService } from "@web/core/utils/hooks";



export class TowerDashboard extends Component {
  static template = "tower_london.TowerDashboard";
   setup() {
        this.orm = useService("orm");
        this.charts = {};
        this.state = useState({
            patients: [],
            selectedPatient: null,
            data: {},
        });
        this.chartRef = useRef("chartRef");

        onWillStart(async () => {
            const data = await this.orm.call("tower.of.london", "get_dashboard_data", []);
            this.state.data = data;
            this.state.patients = Object.keys(data);
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

        const ctx = this.chartRef.el.getContext("2d");
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
                        text: `Z-Scores for ${patient}`
                    }
                }
            }
        });
    }


    selectPatient(ev) {
      const patientName = ev.currentTarget.dataset.patient;
      this.state.selectedPatient = patientName;
      this.renderChart();
}
}

const actionRegistry = registry.category("actions");
actionRegistry.add("tower_london.dashboard", TowerDashboard);
export default TowerDashboard;

document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById('graficoHoras');

    if (canvas) {
        const aprovadas = JSON.parse(canvas.dataset.aprovadas || '[]');
        const pendentes = JSON.parse(canvas.dataset.pendentes || '[]');

        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
                datasets: [
                    {
                        label: 'Horas Aprovadas',
                        data: aprovadas,
                        backgroundColor: '#7c3aed',
                        borderColor: '#6d28d9',
                        borderWidth: 1,
                        borderRadius: 6
                    },
                    {
                        label: 'Em Análise / Pendentes',
                        data: pendentes,
                        backgroundColor: '#c084fc',
                        borderColor: '#a855f7',
                        borderWidth: 1,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#1e293b',
                            font: { size: 12, weight: '600' },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 27, 75, 0.95)',
                        titleColor: '#ffffff',
                        bodyColor: '#f8fafc',
                        titleFont: { size: 13, weight: 'bold' },
                        bodyFont: { size: 13 },
                        padding: 10,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: { display: false },
                        ticks: {
                            color: '#1e293b',
                            font: { size: 12, weight: '700' }
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(30, 41, 59, 0.1)'
                        },
                        ticks: {
                            color: '#1e293b',
                            font: { size: 12, weight: '600' }
                        }
                    }
                }
            }
        });
    }
});

const ctx = document.getElementById('subjectChart').getContext('2d');
new Chart(ctx, {
    type: 'doughnut',
    data: {
        // Parse JSON data passed from the backend
        labels: JSON.parse('{{ chart_labels | safe }}'),
        datasets: [{
            data: JSON.parse('{{ chart_data | safe }}'),
            backgroundColor: ['#FBBF24', '#4F46E5', '#A855F7', '#10B981', '#F472B6'],
            borderWidth: 0
        }]
    },
    options: { 
        responsive: true, 
        maintainAspectRatio: false, 
        plugins: { legend: { position: 'right' } } 
    }
});

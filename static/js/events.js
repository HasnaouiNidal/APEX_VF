document.addEventListener('DOMContentLoaded', function() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const events = document.querySelectorAll('.event-item');
    const noEventsMsg = document.getElementById('no-events-msg');

    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Update Active Class
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            const filterValue = button.getAttribute('data-filter');
            let visibleCount = 0;

            // Show/Hide Logic
            events.forEach(event => {
                const category = event.getAttribute('data-category');
                
                if (filterValue === 'all' || category === filterValue) {
                    event.classList.remove('d-none');
                    event.style.opacity = '0';
                    setTimeout(() => event.style.opacity = '1', 50); // Small fade-in effect
                    visibleCount++;
                } else {
                    event.classList.add('d-none');
                }
            });

            // Handle Empty Message
            noEventsMsg.classList.toggle('d-none', visibleCount > 0);
        });
    });
});
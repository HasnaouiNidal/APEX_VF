document.addEventListener('DOMContentLoaded', function() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const articles = document.querySelectorAll('.article-item');
    const noResultsMsg = document.getElementById('no-results-msg');

    // Define Subject Groups
    const groups = {
        'Sciences': ['Mathematics', 'Physics & Chemistry', 'SVT', 'Sport'],
        'Languages': ['Arabe', 'Francais', 'Anglais'],
        'other': ['Primaire', 'Education_islamique', 'H&G'],
        
    }; 

    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Update UI
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            const filterValue = button.getAttribute('data-filter');
            let visibleCount = 0;

            // Filter Items
            articles.forEach(article => {
                const subject = article.getAttribute('data-subject');
                let shouldShow = false;

                if (filterValue === 'all') {
                    shouldShow = true;
                } else if (groups[filterValue] && groups[filterValue].includes(subject)) {
                    shouldShow = true;
                }

                if (shouldShow) {
                    article.classList.remove('d-none');
                    visibleCount++;
                } else {
                    article.classList.add('d-none');
                }
            });

            // Show Empty Msg
            noResultsMsg.classList.toggle('d-none', visibleCount > 0);
        });
    });
});
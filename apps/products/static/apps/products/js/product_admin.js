document.addEventListener('DOMContentLoaded', function () {
    const categoriesSelect = document.getElementById('id_categories');
    const subcategoriesSelect = document.getElementById('id_subcategories');

    if (!categoriesSelect || !subcategoriesSelect) {
        return;
    }

    const pathSegments = window.location.pathname.split('/').filter(Boolean);
    let basePath = window.location.pathname;

    if (pathSegments[pathSegments.length - 1] === 'add') {
        basePath = '/' + pathSegments.slice(0, -1).join('/') + '/';
    } else if (pathSegments[pathSegments.length - 1] === 'change') {
        basePath = '/' + pathSegments.slice(0, -2).join('/') + '/';
    }

    const endpoint = basePath + 'ajax/get-subcategories/';

    function fetchSubcategories() {
        const selectedIds = Array.from(categoriesSelect.selectedOptions)
            .map(option => option.value)
            .filter(Boolean);

        const url = new URL(endpoint);
        if (selectedIds.length > 0) {
            url.searchParams.set('category_ids', selectedIds.join(','));
        }

        fetch(url.toString(), {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    return;
                }

                const selectedValues = new Set(
                    Array.from(subcategoriesSelect.selectedOptions).map(option => option.value)
                );
                subcategoriesSelect.innerHTML = '';

                data.subcategories.forEach(subcategory => {
                    const option = document.createElement('option');
                    option.value = subcategory.id;
                    option.text = subcategory.name;
                    if (selectedValues.has(String(subcategory.id))) {
                        option.selected = true;
                    }
                    subcategoriesSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading subcategories:', error);
            });
    }

    categoriesSelect.addEventListener('change', fetchSubcategories);

    if (categoriesSelect.selectedOptions.length > 0) {
        fetchSubcategories();
    }
});

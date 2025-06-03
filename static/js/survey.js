document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const submitBtn = document.getElementById('submitBtn');
    const surveyForm = document.getElementById('surveyForm');
    const ratingCircles = document.querySelectorAll('.rating-circle');

    // Initialize rating circles
    ratingCircles.forEach(circle => {
        circle.addEventListener('click', function() {
            const value = this.getAttribute('data-value');
            const name = this.getAttribute('data-name');
            selectRating(name, value, this);
        });

        // Add hover effects
        circle.addEventListener('mouseenter', function() {
            if (!this.classList.contains('selected')) {
                this.classList.add('hover');
            }
        });

        circle.addEventListener('mouseleave', function() {
            this.classList.remove('hover');
        });

        // Make circles focusable for accessibility
        circle.setAttribute('tabindex', '0');
        circle.setAttribute('role', 'button');
        circle.setAttribute('aria-label', `Avaliar ${circle.getAttribute('data-value')} de 10`);
    });

    function selectRating(name, value, selectedElement) {
        // Update hidden input with proper mapping
        let hiddenInput;
        const inputMap = {
            'overall_rating': 'overallRating',
            'air_rating': 'airRating',
            'guides_rating': 'guidesRating',
            'hotel_1_rating': 'hotel1Rating',
            'hotel_2_rating': 'hotel2Rating',
            'restaurants_rating': 'restaurantsRating',
            'activities_rating': 'activitiesRating'
        };

        const inputId = inputMap[name];
        if (inputId) {
            hiddenInput = document.getElementById(inputId);
            if (hiddenInput) {
                hiddenInput.value = value;
                console.log(`Set ${name} to ${value}`); // Debug log
            } else {
                console.error(`Hidden input not found for ${name} (${inputId})`);
            }
        }

        // Update visual state for this rating group
        const groupCircles = document.querySelectorAll(`[data-name="${name}"]`);
        groupCircles.forEach(circle => {
            circle.classList.remove('selected', 'hover');
        });
        selectedElement.classList.add('selected');

        // Hide error message if exists
        const errorElement = document.getElementById(name + 'Error');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }

    function validateForm() {
        let isValid = true;

        // Check overall rating (mandatory)
        const overallRating = document.getElementById('overallRating').value;
        const overallError = document.getElementById('overallRatingError');

        if (!overallRating) {
            if (overallError) {
                overallError.style.display = 'block';
            }
            isValid = false;
        } else {
            if (overallError) {
                overallError.style.display = 'none';
            }
        }

        // Validate conditional questions - only if visible
        if (!validateConditionalRating('used_air_travel', 'air_rating')) {
            isValid = false;
        }
        
        // Only validate guides if the guides section exists in the DOM
        const guidesSection = document.querySelector('input[name="had_guides"]');
        if (guidesSection && !validateConditionalRating('had_guides', 'guides_rating')) {
            isValid = false;
        }
        
        if (!validateConditionalRating('had_restaurants', 'restaurants_rating')) {
            isValid = false;
        }
        if (!validateConditionalRating('had_activities', 'activities_rating')) {
            isValid = false;
        }

        // Validate hotel ratings - only if hotel containers exist and are visible
        const hotel1Input = document.getElementById('hotel1Rating');
        if (hotel1Input && !validateHotelRating('hotel1Rating')) {
            isValid = false;
        }
        
        const hotel2Input = document.getElementById('hotel2Rating');
        if (hotel2Input && !validateHotelRating('hotel2Rating')) {
            isValid = false;
        }

        return isValid;
    }

    function validateConditionalRating(triggerName, ratingName) {
        const triggerYes = document.querySelector(`input[name="${triggerName}"][value="sim"]`);
        const ratingInput = document.getElementById(ratingName.replace('_', '') + 'Rating') || 
                           document.getElementById(ratingName.charAt(0).toLowerCase() + ratingName.slice(1).replace('_', '') + 'Rating');
        
        // Get the conditional question container
        const conditionalContainer = document.getElementById(ratingName.replace('_', '-'));
        
        // Only validate if the question is visible (trigger is "sim" and container is displayed)
        if (triggerYes && triggerYes.checked && conditionalContainer && 
            conditionalContainer.style.display !== 'none' && 
            ratingInput && !ratingInput.value) {
            // Show error for conditional rating
            const errorElement = document.getElementById(ratingName + 'Error');
            if (errorElement) {
                errorElement.style.display = 'block';
                errorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return false;
        }
        return true;
    }

    function validateHotelRating(ratingInputId) {
        const ratingInput = document.getElementById(ratingInputId);
        const hotelContainer = ratingInput ? ratingInput.closest('.hotel-rating') : null;
        
        // Only validate if the hotel container exists, is visible, and has no rating
        if (ratingInput && hotelContainer && 
            hotelContainer.style.display !== 'none' && 
            !ratingInput.value) {
            // Create error message if it doesn't exist
            let errorElement = document.getElementById(ratingInputId + 'Error');
            if (!errorElement) {
                errorElement = document.createElement('div');
                errorElement.id = ratingInputId + 'Error';
                errorElement.className = 'rating-error';
                errorElement.style.display = 'none';
                errorElement.textContent = 'Por favor, avalie este hotel';
                ratingInput.parentNode.appendChild(errorElement);
            }
            errorElement.style.display = 'block';
            errorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return false;
        }
        return true;
    }

    function showLoadingState() {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
        }
    }

    // Form submission handler
    if (surveyForm) {
        surveyForm.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
            } else {
                showLoadingState();
            }
        });
    }
});

// Function to toggle conditional questions
function toggleConditionalQuestion(questionId, show) {
    const question = document.getElementById(questionId);
    if (question) {
        question.style.display = show ? 'block' : 'none';

        // Clear rating if hiding the question
        if (!show) {
            const ratingCircles = question.querySelectorAll('.rating-circle');
            ratingCircles.forEach(circle => {
                circle.classList.remove('selected');
            });

            // Clear hidden input
            const hiddenInput = question.querySelector('input[type="hidden"]');
            if (hiddenInput) {
                hiddenInput.value = '';
            }
        }
    }
}
// Add animation effects, if needed
document.addEventListener('DOMContentLoaded', function() {
    // Animation for feature boxes
    const featureBoxes = document.querySelectorAll('.feature-box, .mission-box, .offer-box');
    
    if (featureBoxes.length > 0) {
        featureBoxes.forEach(box => {
            box.addEventListener('mouseenter', function() {
                this.style.transition = 'transform 0.3s, box-shadow 0.3s';
                this.style.transform = 'translateY(-5px)';
                this.style.boxShadow = '0 10px 20px rgba(0, 0, 0, 0.3)';
            });
            
            box.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = 'none';
            });
        });
    }
    
    });
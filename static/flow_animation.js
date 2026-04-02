class FlowAnimation {
    constructor() {
        this.canvas = document.getElementById('bg-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.mouse = { x: -1000, y: -1000 };
        this.particles = [];
        this.particleCount = 15;
        this.ribbonLength = 40;
        this.hue = 0;
        
        this.init();
        this.animate();
        this.setupListeners();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());
        
        for (let i = 0; i < this.particleCount; i++) {
            this.particles.push(new Particle(this.canvas.width, this.canvas.height, this.ribbonLength));
        }
    }

    resize() {
        this.canvas.width = window.innerWidth * window.devicePixelRatio;
        this.canvas.height = window.innerHeight * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        this.canvas.style.width = window.innerWidth + 'px';
        this.canvas.style.height = window.innerHeight + 'px';
    }

    setupListeners() {
        window.addEventListener('mousemove', (e) => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        });
        
        window.addEventListener('touchstart', (e) => {
            if (e.touches[0]) {
                this.mouse.x = e.touches[0].clientX;
                this.mouse.y = e.touches[0].clientY;
                this.burst(this.mouse.x, this.mouse.y);
            }
        });

        window.addEventListener('mousedown', (e) => {
            this.burst(e.clientX, e.clientY);
        });
    }

    burst(x, y) {
        for (let i = 0; i < 5; i++) {
            const p = new Particle(this.canvas.width, this.canvas.height, this.ribbonLength);
            p.x = x;
            p.y = y;
            p.velocity.x = (Math.random() - 0.5) * 10;
            p.velocity.y = (Math.random() - 0.5) * 10;
            this.particles.push(p);
            
            // Keep particle count under control
            if (this.particles.length > 50) this.particles.shift();
        }
    }

    animate() {
        // Clear logical area using the current transform
        this.ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
        
        this.hue = (this.hue + 0.2) % 360;
        
        this.particles.forEach((p, i) => {
            p.update(this.mouse);
            p.draw(this.ctx, this.hue + (i * 20));
        });
        
        requestAnimationFrame(() => this.animate());
    }
}

class Particle {
    constructor(canvasWidth, canvasHeight, ribbonLength) {
        this.x = Math.random() * (canvasWidth / window.devicePixelRatio);
        this.y = Math.random() * (canvasHeight / window.devicePixelRatio);
        this.history = [];
        this.ribbonLength = ribbonLength;
        this.velocity = {
            x: (Math.random() - 0.5) * 2,
            y: (Math.random() - 0.5) * 2
        };
        this.friction = 0.96;
        this.ease = 0.05;
    }

    update(mouse) {
        // Attraction to mouse
        let dx = mouse.x - this.x;
        let dy = mouse.y - this.y;
        let distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < 600) {
            this.velocity.x += dx * 0.0001 * (600 - distance) / 600;
            this.velocity.y += dy * 0.0001 * (600 - distance) / 600;
        }

        // Random jitter
        this.velocity.x += (Math.random() - 0.5) * 0.1;
        this.velocity.y += (Math.random() - 0.5) * 0.1;

        this.velocity.x *= this.friction;
        this.velocity.y *= this.friction;

        this.x += this.velocity.x;
        this.y += this.velocity.y;

        // Wrap around
        const margin = 100;
        if (this.x < -margin) this.x = window.innerWidth + margin;
        if (this.x > window.innerWidth + margin) this.x = -margin;
        if (this.y < -margin) this.y = window.innerHeight + margin;
        if (this.y > window.innerHeight + margin) this.y = -margin;

        this.history.unshift({ x: this.x, y: this.y });
        if (this.history.length > this.ribbonLength) {
            this.history.pop();
        }
    }

    draw(ctx, hue) {
        if (this.history.length < 2) return;

        ctx.beginPath();
        ctx.moveTo(this.history[0].x, this.history[0].y);
        
        for (let i = 1; i < this.history.length; i++) {
            const p = this.history[i];
            const prev = this.history[i - 1];
            const xc = (p.x + prev.x) / 2;
            const yc = (p.y + prev.y) / 2;
            ctx.quadraticCurveTo(prev.x, prev.y, xc, yc);
        }

        const gradient = ctx.createLinearGradient(
            this.history[0].x, this.history[0].y,
            this.history[this.history.length - 1].x, this.history[this.history.length - 1].y
        );
        
        gradient.addColorStop(0, `hsla(${hue}, 100%, 70%, 0.8)`);
        gradient.addColorStop(1, `hsla(${(hue + 60) % 360}, 100%, 50%, 0)`);
        
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 1.5;
        ctx.lineCap = 'round';
        ctx.stroke();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new FlowAnimation();
});

# 🏎️ 2D Sideway Showdown

A high-octane, top-down 2D racing game developed in Python using Pygame. Experience physics-based car handling, a dynamic drifting system, and an interactive garage UI to swap cars on the fly!

* **Version:** Alpha rd260415_0823
* **Developer:** J4N3 (v10.0.19045.6456)
* **Language:** Python 3.x

---

## ✨ Core Features

* **Advanced 2D Physics:** Realistic acceleration, braking, momentum, and rolling friction.
* **Drift Mechanics:** A custom drift system that allows you to slide through corners. Drifting increases your turn radius and leaves dynamic tire marks on the track, but comes at the cost of speed.
* **Dynamic Camera & Zoom:** The camera smoothly tracks your car. You can seamlessly zoom in and out of the action (`SHIFT + Mouse Wheel`), with the entire map scaling dynamically without losing focus.
* **Interactive Garage UI:** Pause the game mid-drive by pressing a single key (`C`) to open a sleek, transparent overlay menu and switch between different hypercars (Toyota Altezza, McLaren 600LT, Pagani Utopia, etc.).
* **Off-Road Penalty:** Drive carefully! Mask-based collision detection ensures your car significantly slows down if you veer off the asphalt and onto the grass.
* **Smart Asset Loading:** Built-in fallback renderer. If images are missing, the game safely generates procedural shapes so it never crashes!

---

## 🎮 How to Play

### Controls
| Key | Action |
| :--- | :--- |
| **`W`** | Accelerate Forward |
| **`S`** | Brake / Reverse |
| **`A`** / **`D`** | Turn Left / Turn Right |
| **`SPACE`** | **Drift!** (Hold while turning) |
| **`SHIFT` + `Scroll`** | Zoom Camera In / Out (11 Levels) |
| **`C`** | Open / Close Car Selection Menu |
| **`ESC`** | Quit Game |

### Driving Tips
1. **Master the Drift:** Don't just hold `SPACE` everywhere. Use it right before entering a sharp corner to swing the tail out. Remember, drifting reduces your speed, so release it as you exit the apex to accelerate again!
2. **Off-Roading is Slow:** The green grass has a high friction multiplier. If you get pushed off the track, release the gas and steer back onto the gray asphalt to regain traction.

---

## 🛠️ Installation & Setup

### Running from Source
1. Ensure you have Python 3.x installed.
2. Install the required libraries:
   ```bash
   pip install pygame numpy

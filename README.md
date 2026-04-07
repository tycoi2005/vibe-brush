# 🎨 Open Brush AI Sculptor

Create 3D art in [Open Brush](https://openbrush.app/) using natural language. Type what you want, and an AI agent translates your words into 3D brush strokes.

**Draw in one line:**
```bash
python -m sculptor.cli --prompt "draw a glowing spiral tower with orbiting rings" -d
```

**Or launch the interactive mode:**
```text
🖌️  sculptor> draw a glowing spiral tower with orbiting rings

🎨 Glowing Spiral Tower
   Steps: 10
   - set_brush: 3x
   - set_color: 4x
   - draw_shape: 3x
Execute this plan? [y/n/r]: y

  ✓ Completed: 10/10 steps
  ✓ Paths drawn: 305
```

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Open Brush** installed with API enabled ([setup guide](docs/install_openbrush.md))
- An **OpenAI-compatible API key** (OpenAI, Anthropic via proxy, Ollama, etc.)

### Install

```bash
# Clone this repo
git clone https://github.com/your-username/openbrush-vibe-sculpturing.git
cd openbrush-vibe-sculpturing

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp config.example.yaml config.yaml
# Edit config.yaml with your API key and settings
```

Or use environment variables:
```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional, default is OpenAI
```

### Run

1. **Start Open Brush** (with monoscopic mode and API enabled)
2. **Launch the sculptor:**
   ```bash
   python -m sculptor.cli
   ```

3. **Type what you want to create!**

## CLI Commands

| Command | Description |
|---------|-------------|
| `/new` | Clear the canvas |
| `/save [name]` | Save the sketch |
| `/export` | Export to glTF/OBJ |
| `/undo` | Undo last action |
| `/redo` | Redo |
| `/refine <feedback>` | Modify the last artwork |
| `/status` | Check Open Brush connection |
| `/reset` | Clear conversation history |
| `/help` | Show help |
| `/quit` | Exit |

## Non-Interactive Mode

Execute a single prompt from the command line:

```bash
python -m sculptor.cli --prompt "create a fractal tree with autumn colors"
```

## How It Works

```
User Prompt  →  LLM (GPT-4/etc.)  →  Art Plan (JSON)  →  Executor  →  Open Brush API
                                                                          ↓
                                                                     3D Art! 🎨
```

1. **You describe** what you want in natural language
2. **The LLM** generates a structured JSON art plan with shape primitives, colors, and brushes
3. **The executor** translates the plan into HTTP API commands
4. **Open Brush** renders the 3D art in real-time

## Available Shape Primitives

The AI can use these parametric shapes:

| Shape | Description |
|-------|-------------|
| `circle` | Circle in any plane (XY, XZ, YZ) |
| `helix` | 3D spiral/helix |
| `spiral` | Flat Archimedean spiral |
| `lissajous` | 3D Lissajous curves |
| `polygon` | Regular N-sided polygon |
| `star` | Star with inner/outer radius |
| `sphere_wireframe` | Wireframe sphere |
| `cube_wireframe` | Wireframe cube |
| `torus` | Donut/torus rings |
| `cylinder_wireframe` | Wireframe cylinder |
| `cone_wireframe` | Wireframe cone |
| `tree` | Fractal tree with branches |
| `wave_surface` | Rippling wave surface |
| `mountain_range` | Terrain with peaks |
| `line` | Straight line |
| `grid` | Grid of lines |

## Configuration

See [config.example.yaml](config.example.yaml) for all options:

```yaml
llm:
  api_key: "sk-..."
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o"
  temperature: 0.7

openbrush:
  host: "localhost"
  port: 40074
  command_delay: 0.05

export:
  auto_save: true
  auto_export: false
```

## Examples

```bash
# Geometric art
🖌️  sculptor> create a wireframe sphere inside a torus with neon colors

# Nature scene
🖌️  sculptor> draw a forest of fractal trees on a mountain landscape

# Abstract art
🖌️  sculptor> make an abstract lissajous pattern with rainbow colors and glow

# Architecture
🖌️  sculptor> build a pagoda tower using cubes and cones stacked vertically
```

## Setting Up Open Brush

See the detailed [Open Brush Installation Guide](docs/install_openbrush.md) for:
- Installing on macOS, Windows, Linux
- Enabling Monoscopic Mode (no VR headset needed)
- Enabling the HTTP API
- Troubleshooting

## License

MIT

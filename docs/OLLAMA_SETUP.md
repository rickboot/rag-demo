# Ollama setup (Mac)

Phase 2 chat uses **Ollama** on the Mac for the dev model. If you see “can’t find Ollama” or the chat returns 503:

---

## Install and run Ollama

1. **Install the app**  
   - Download from [ollama.com](https://ollama.com) and open the Mac app, or:  
   - `brew install ollama` (then start the service: `brew services start ollama`).

2. **Start Ollama**  
   - If you installed the **GUI**: open **Ollama** from Applications (or the menu bar). The CLI talks to this app.  
   - If you used **Homebrew**: the `ollama` CLI is in your PATH; the service listens on `localhost:11434`.

3. **Pull a model**  
   In a terminal:
   ```bash
   ollama run llama3.1:8b
   ```
   (Llama 3.2 has no 8B on Ollama — only 1B/3B. For 8B use **llama3.1:8b**. Smaller option: `ollama run llama3.2` for 3B. Set `MODEL_NAME` in `.env` to match.)

4. **If the CLI says it “can’t find Ollama”**  
   - **GUI install:** Make sure the Ollama **app is actually running** (menu bar icon or in Applications). The CLI expects the app to be open.  
   - **Homebrew:** Run `brew services start ollama` and check `curl http://localhost:11434/api/tags` to see if the server is up.

---

## Check that Ollama is reachable

```bash
curl http://localhost:11434/api/tags
```

If you get JSON with a `models` list, the backend can use Ollama.

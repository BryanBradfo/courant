# Adding a new ambient scene to Courant

Scenes are looping videos that play full-screen behind the cozy panel.
Adding a new one is a 2-step process : find a video and register it.

## 1. Find a CC0 / permissively licensed video

Good sources :

- [Pixabay videos](https://pixabay.com/videos/)
- [Pexels videos](https://www.pexels.com/videos/)
- [Coverr](https://coverr.co/)
- [Mixkit](https://mixkit.co/free-stock-video/)

Search for the vibe you want : "rainy cafe", "night train", "cozy fireplace", etc.

Criteria :
- Looping (or close — start/end frames similar)
- 15-30 seconds
- 720p or 1080p, MP4 (H.264)
- Under 30 MB ideally
- Subtle motion (no zoom, no cuts, no flashes)
- No watermarks or text overlays

## 2. Extract the direct MP4 URL

On the Pixabay/Pexels page, right-click on the embedded video and
copy the video URL. You should get something like
`https://cdn.pixabay.com/video/.../file-12345-720.mp4`.

## 3. Add to `courant/data/scenes.json`

```json
{
  "your-slug-here": {
    "name": "Display Name",
    "url": "https://cdn.pixabay.com/video/...-720.mp4",
    "theme": "dark",
    "author": "Pixabay user @name",
    "license": "Pixabay Content License",
    "source": "https://pixabay.com/videos/your-video-page/"
  }
}
```

- `slug` : short, kebab-case, used in the URL and DB
- `theme` : `dark` for night/dim scenes, `light` for bright scenes (controls panel contrast)
- `author` and `license` get displayed on the `/credits` page

That's it. The scene appears in the dropdown automatically.

## 4. Test locally

```bash
courant start
```

Open the web UI, go to Settings, switch to your new scene. The video
should load and start looping. If it fails, check the browser console
for errors (CORS, 404, format).

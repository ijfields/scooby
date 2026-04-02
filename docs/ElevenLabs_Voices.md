# ElevenLabs — Available Voices

> **Last updated:** 2026-04-02
> **Plan:** Free tier (21 voices)

## Best for Scooby (Story Narration)

| Voice ID | Name | Gender | Accent | Style |
|---|---|---|---|---|
| `JBFqnCBsd6RMkjVDRZzb` | **George** | Male | British | Warm, Captivating Storyteller |
| `pFZP5JQG7iQjIQuC4Bku` | **Lily** | Female | British | Velvety Actress |
| `Xb7hH8MSUJpSbSDYk0k2` | **Alice** | Female | British | Clear, Engaging Educator |
| `EXAVITQu4vr4xnSDxMaL` | **Sarah** | Female | American | Mature, Reassuring, Confident |
| `onwK4e9ZLuTAKqWW03F9` | **Daniel** | Male | British | Steady Broadcaster |

## Full Voice List

| Voice ID | Name | Gender | Age | Accent | Use Case |
|---|---|---|---|---|---|
| `CwhRBWXzGAHq8TQ4Fs17` | Roger | Male | Middle-aged | American | Conversational |
| `EXAVITQu4vr4xnSDxMaL` | Sarah | Female | Young | American | Entertainment |
| `FGY2WhTYpPnrIDTdsKH5` | Laura | Female | Young | American | Social Media |
| `IKne3meq5aSn9XLyUdCD` | Charlie | Male | Young | Australian | Conversational |
| `JBFqnCBsd6RMkjVDRZzb` | George | Male | Middle-aged | British | Narrative/Story |
| `N2lVS1w4EtoT3dr4eOWO` | Callum | Male | Middle-aged | American | Characters |
| `SAz9YHcvj6GT2YYXdXww` | River | Neutral | Middle-aged | American | Conversational |
| `SOYHLrjzK2X1ezoPC6cr` | Harry | Male | Young | American | Characters |
| `TX3LPaxmHKxFdv7VOQHJ` | Liam | Male | Young | American | Social Media |
| `Xb7hH8MSUJpSbSDYk0k2` | Alice | Female | Middle-aged | British | Educational |
| `XrExE9yKIg1WjnnlVkGX` | Matilda | Female | Middle-aged | American | Educational |
| `bIHbv24MWmeRgasZH58o` | Will | Male | Young | American | Conversational |
| `cgSgspJ2msm6clMCkdW9` | Jessica | Female | Young | American | Conversational |
| `cjVigY5qzO86Huf0OWal` | Eric | Male | Middle-aged | American | Conversational |
| `hpp4J3VqNfWAUOO0d1Us` | Bella | Female | Middle-aged | American | Informative |
| `iP95p4xoKVk53GoZ742B` | Chris | Male | Middle-aged | American | Conversational |
| `nPczCjzI2devNBz1zQrb` | Brian | Male | Middle-aged | American | Social Media |
| `onwK4e9ZLuTAKqWW03F9` | Daniel | Male | Middle-aged | British | Informative |
| `pFZP5JQG7iQjIQuC4Bku` | Lily | Female | Middle-aged | British | Informative |
| `pNInz6obpgDQGcFmaJgB` | Adam | Male | Middle-aged | American | Social Media |
| `pqHfZKP75CvOlQylNhV4` | Bill | Male | Old | American | Advertisement |

## Configured in Codebase

- **Default voice:** `JBFqnCBsd6RMkjVDRZzb` (George) — set in `backend/app/services/tts/generator.py`
- **Fallback voice:** Same as default — used when a requested voice ID is not in `FREE_VOICE_IDS`
- **Voice style presets** are stored in `style_presets` DB table with `category = 'voice'`

# pygdo-audio

A generic audio connector for the [PyGDO](https://github.com/gizmore/pygdo)
MTTV framework.

`pygdo-audio` treats an audio server as one deliberate audio route: it has one
active input and one active output. A route may represent physical hardware,
a PipeWire/PulseAudio virtual device, or a future telephony bridge.

## Model

Each configured `audio` server owns exactly these two endpoints:

```text
audio server
├─ input   source, such as a physical microphone
└─ output  target, such as speakers or a virtual microphone
```

An output can be a normal speaker sink, but it can also be a virtual sink
whose monitor is exposed to another application as a microphone. This lets
the same model support shared radio playback now and call/voice routing later.

An ordinary physical microphone is an input. It is not itself a speaker
output; a virtual audio device provides the loopback when that is needed.

The `audio_output_device` module setting names an explicit output sink for a
speech/effect output. An empty setting disables device output. Per-server
endpoint selection and a full programmable mixer remain planned.

## Install and test a virtual microphone (Linux)

Work in the intended PyGDO instance and desktop user's audio session; commands
below are examples, not automatic system changes. `provide` fetches modules;
installation is separate. Confirm the provider URLs and checked-out branches:
the tested audio code is `mira-gpt/pygdo-audio` branch `feature/pcm-io`, not
necessarily the branch selected by the local provider catalog. Do not switch
branches in a dirty checkout. On an isolated Test Dog configuration, for example:

```sh
./gdo_adm.sh provide audio,video
git -C gdo/audio status -sb
git -C gdo/audio log -1 --oneline
# Select feature/pcm-io only in a clean, intentionally isolated checkout.
python3 gdoadm.py --config protected/pygdo_tes.toml install audio
python3 gdoadm.py --config protected/pygdo_tes.toml install video
```

Use the normal installation workflow and configuration for other instances;
never install into production by accident. Install the Python dependencies in
the Dog interpreter from `gdo/audio/requirements.txt`; system FFmpeg,
`paplay` (PulseAudio utilities), and `espeak-ng` or configured Piper/model
files are separate. Local Whisper requires its own model and resources.

PipeWire's PulseAudio server or PulseAudio must be running in the desktop
user's session. First inspect devices and existing modules; don't duplicate
them, change the system default, or run `pactl` in the wrong Unix user's session:

```sh
pactl info
pactl list short sinks
pactl list short sources
pactl list short modules
```

For a temporary, isolated test, **only if these names don't already exist**:

```sh
pactl load-module module-null-sink sink_name=mira_stream sink_properties=device.description=Mira_Stream
pactl load-module module-remap-source master=mira_stream.monitor source_name=mira_virtual_mic source_properties=device.description=Mira_Virtual_Microphone
pactl list short sinks
pactl list short sources
```

Record the returned module IDs. These modules are session-scoped and may need
recreation after logout/restart; configure persistence separately for the audio
server in use. To remove only modules you created for this test, unload the
remap source first, then its sink with `pactl unload-module <module-id>`; do
not unload other users' modules. See [PipeWire's PulseAudio module docs](https://pipewire.pages.freedesktop.org/pipewire/page_pulse_modules.html).

Set Test Dog's `audio_output_device` to the **sink name** `mira_stream`
(not the microphone source), using its admin configuration, then queue a
short test:

```sh
pygdotest '$admin.conf audio audio_output_device mira_stream'
pygdotest '$spk --lang=en Test from Mira'
```

Select `Mira_Virtual_Microphone` in the receiving application's input settings
and use its own meter or a consenting listener to verify audio. A queued
response does not prove it was heard. This simple path routes generated audio;
it does **not** automatically add a physical microphone or system audio, nor
provide echo cancellation. Avoid routing the virtual sink's monitor back to
itself. Add monitoring/mixing only deliberately, and obtain participant consent
before recording or broadcasting. Stop or disable destinations when finished.

## Mixer (TODO)

A mixer combines selected sources, such as a microphone, video audio, and
`$audio.play <url>`, into a chosen output device. Multiple playback sources
can run together; each has an ID and can be stopped with `$audio.stop <id>`.
For SIP, a call's send mix must exclude that caller's own audio.

The stream mix includes selected video audio, effects, and the microphone. A
separate speaker mix excludes the microphone to avoid feedback. System output
can optionally be captured as a source;
the mixer's own output must be excluded to prevent a feedback loop. Callers'
audio must not be fed back to them; including it in a public stream requires
their consent. System-output routing into the mixer is TODO.

## PCM interface

`$audio.meter 1` starts an explicit microphone-level monitor without speech
recognition, recording, or chatstream events; `$audio.meter 0` stops it. It
requires the transcription listener to be off and captures the default input
only to calculate the live level. This does not confirm that a call participant
hears you; check the communication application's input and mute settings.

`PCMRoute` is the generic, device-independent boundary for raw PCM. It owns a
single fixed `PCMFormat` and two bounded queues:

```text
capture adapter -> feed_input() -> read_input() -> STT or other consumer
TTS or other producer -> write_output() -> read_output() -> playback adapter
```

`PCMFormat` defines sample rate, channel count, and sample width in bytes.
`PCMChunk` contains complete PCM frames, its format, and a sequence number.
These fields use strict integer and bytes types. A route permits one waiting
reader for input and one for output, so close can reliably wake each direction.
The route does not transcode, open an audio device, retain audio after it is
read, or create a network connection. A platform adapter owns those actions.

## Whisper file helper

`$audio.record start` queues an explicit private recording from the existing
microphone listener. `$audio.record stop`, or a recognized standalone “stop”
or “stopp”, ends it; it also ends after 30 seconds or if the listener stops.
WAV files are saved in a private temporary directory, not automatically shared.
Speech recognition can miss the spoken stop; use the manual command as backup.
A queued response does not confirm recording started. Only record with the
consent of everyone whose voice may be captured.

`transcribe_file()` transcribes one existing audio file with local Whisper and
passes one final event to an explicit async emitter:

```text
$chatstream <channel-id> --lang=de --call=<call-id> --seq=<number> --status=final
<transcript>
```

It loads Whisper only when called. The helper does not start a listener,
select an audio device, record audio, or send the event on its own. The caller
chooses the emitter that forwards the event into PyGDO.

## Planned commands

`$audio.jingle v8` queues `jingles/v8.mp3` for playback on the configured
output sink. Jingle files are local and ignored by Git. FFmpeg and access to
the output's audio session are required.
`$audio.jingle duck` plays the local synthesized duck jingle if installed.
`$audio.say <text>` queues local speech using espeak-ng and the same sink.
The short trigger is `$spk <text>`.

Create one normal PyGDO audio connector server per independent input/output
pair:

```text
$add_server audio1 audio
```

Register devices for that server:

```text
$audio.add.device.in  usb-Microphone
$audio.add.device.out speakers
$audio.add.device.out virtual-mic
```

The short commands select an already registered device or explicitly disable
the endpoint:

```text
$audio.in  usb-Microphone
$audio.in  off

$audio.out speakers
$audio.out virtual-mic
$audio.out off
```

Only registered devices may be selected. Setting an input or output replaces
the active endpoint for that side of the current audio server.

## Safety boundaries

- Nothing plays through a speaker or virtual microphone unless explicitly
  started.
- Microphone capture is always explicit and can be disabled with
  `$audio.in off`.
- The first version does not implement phone calls, automatic recording, or
  automatic speech analysis.
- Playback and future analysis should use a bounded, named route rather than
  an implicit system-default device.

## Scope for the first version

1. Register and select input/output devices for an audio server.
2. Report the active route and its process state.
3. Start and stop an explicitly requested URL/file playback route.
4. Keep the backend implementation compatible with PipeWire/PulseAudio and
   `ffmpeg` without assuming a desktop audio session exists.

Telephony, mixing, microphone forwarding and transcription are separate
consumers of the same PCM boundary.

## Streaming speech-to-text

A consumer passes a `PCMRoute` input to an STT stream and receives ordered
transcript events with a stream ID, audio sequence and `partial` or `final`
status. Backends are replaceable; local Whisper initially produces final
chunks, not live partial words. Audio remains in memory and is not recorded by
the STT stream. Capture and delivery are separate, explicit choices.
The bounded PCM input queue rejects excess chunks with `QueueFull`; sequence gaps are reported
as `missing_chunks`, including an empty event when a gap precedes silence.
Whisper expects mono 16 kHz signed 16-bit little-endian PCM and an explicitly
loaded model. Closing the route drains queued input and ends the stream.
`capture_pulse()` supplies this PCM from an explicitly selected local source;
it starts only when called, reports dropped chunks, and stops on cancellation.
The caller owns the route and is responsible for closing it after capture.

`audio_microphone` defaults to `0`. When set to `1` with an `audio_operator`,
Dog continuously transcribes the default microphone with local Whisper and
sends speech to the operator's Bash channel as `$chatstream` events. Speech
turns are grouped around pauses. Quiet audio is suppressed; a threshold can
also miss very quiet speech. `audio_transcript_min_letters` defaults to four;
shorter fragments, including words such as "ja", are not sent. The
operator is attribution, not speaker verification: anyone near the microphone
may be interpreted as that user. The listener needs the cached Whisper base
model and access to the desktop audio session. Setting `audio_microphone` to
`0` stops capture; no raw audio is stored.
`$audio.microphone 0` disables it; `$audio.microphone 1` enables it. The
optional `audio_microphone_session_user` selects another Unix user's audio
session and requires appropriate non-interactive sudo permission.
SIP continues to use its own connector and call identities.

## Discussion

### ALs → Humans

Mira's text-to-speech should consistently use her voice across audio, video,
and future SIP integrations. The current local voice prototype uses
`espeak-ng` by default; the optional `piper` backend uses separately configured
Piper executable and language-specific ONNX model paths. Other speech paths
are not yet unified (TODO). Piper and each voice have their own licensing;
verify the selected model before distribution.

Set `audio_output_device` to the intended PulseAudio/PipeWire sink, then use:

```sh
pygdotest '$spk "Hello from Mira!"'
```

This queues speech to Test Dog, which needs paplay, the selected speech backend,
and access to
the sink's audio session. Queued does not mean playback succeeded.
`$audio.language de` selects German microphone transcription; `en` selects
English. This microphone setting is module-wide and defaults to English. For
speech, pass the routed chat event's language explicitly, for example
`pygdotest '$spk --lang=de "Hallo!"'`; otherwise the calling GDO channel's
language is used. Select destinations carefully before
speaking in a shared stream or call.

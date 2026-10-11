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

## PCM interface

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

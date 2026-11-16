package removelink

import (
	"context"
	"encoding/json"
	"errors"
	"sync"
	"time"

	plugins "github.com/landuo/light-media-plugins/internal/sdk"
)

type fileEvent struct {
	Kind, Path, Dest, Mode string
	Directory              bool
	Err                    error
}
type observer interface {
	Events() <-chan fileEvent
	Close()
}
type watchRuntime struct {
	id        uint64
	mu        sync.Mutex
	queue     []fileEvent
	wake      chan struct{}
	stop      chan struct{}
	done      chan struct{}
	once      sync.Once
	finishOne sync.Once
	observers []observer
	specs     []Watch
	pumps     sync.WaitGroup
	active    bool
	closed    bool
}

func newWatchRuntime(id uint64) *watchRuntime {
	return &watchRuntime{id: id, wake: make(chan struct{}, 1), stop: make(chan struct{}), done: make(chan struct{})}
}
func (w *watchRuntime) push(e fileEvent) {
	w.mu.Lock()
	if !w.closed {
		w.queue = append(w.queue, e)
		select {
		case w.wake <- struct{}{}:
		default:
		}
	}
	w.mu.Unlock()
}
func (w *watchRuntime) pop() (fileEvent, bool) {
	w.mu.Lock()
	defer w.mu.Unlock()
	if len(w.queue) == 0 {
		return fileEvent{}, false
	}
	e := w.queue[0]
	w.queue[0] = fileEvent{}
	w.queue = w.queue[1:]
	return e, true
}
func (w *watchRuntime) close() {
	w.once.Do(func() {
		w.mu.Lock()
		w.closed = true
		close(w.stop)
		w.mu.Unlock()
		for _, observer := range w.observers {
			observer.Close()
		}
		w.pumps.Wait()
	})
}
func (w *watchRuntime) finish() { w.finishOne.Do(func() { close(w.done) }) }
func (p *Plugin) addObserver(w *watchRuntime, spec Watch) error {
	watcher, e := p.newObserver(spec)
	if e != nil {
		return e
	}
	w.observers = append(w.observers, watcher)
	w.specs = append(w.specs, spec)
	w.pumps.Add(1)
	go func() {
		defer w.pumps.Done()
		for e := range watcher.Events() {
			e.Mode = spec.Mode
			w.push(e)
		}
	}()
	return nil
}
func (p *Plugin) stopObservers(ctx context.Context) error {
	p.mu.Lock()
	w := p.watch
	p.mu.Unlock()
	if w == nil {
		return nil
	}
	w.close()
	w.mu.Lock()
	active := w.active
	w.mu.Unlock()
	if !active {
		// A not-yet-admitted watch callback will see closed and finish too.
		w.finish()
	}
	select {
	case <-w.done:
	case <-ctx.Done():
		return ctx.Err()
	}
	p.mu.Lock()
	if p.watch == w {
		p.watch = nil
	}
	p.mu.Unlock()
	return nil
}
func (p *Plugin) submitWatch(ctx context.Context, host plugins.HostCaller, w *watchRuntime) error {
	return (plugins.Manager{Host: host}).Submit(ctx, "private_watch", map[string]any{"generation": w.id})
}
func (p *Plugin) runWatch(ctx context.Context, raw json.RawMessage, host plugins.HostCaller) (err error) {
	var in struct{ Generation uint64 }
	if e := json.Unmarshal(raw, &in); e != nil {
		return e
	}
	p.mu.Lock()
	w := p.watch
	p.mu.Unlock()
	if w == nil || w.id != in.Generation {
		return nil
	}
	w.mu.Lock()
	if w.closed || w.active {
		closed := w.closed
		w.mu.Unlock()
		if closed {
			w.finish()
		}
		return nil
	}
	w.active = true
	w.mu.Unlock()
	released := false
	defer func() {
		w.mu.Lock()
		if !released {
			w.active = false
		}
		closed := w.closed
		w.mu.Unlock()
		if err != nil {
			w.close()
			closed = true
		}
		w.mu.Lock()
		active := w.active
		w.mu.Unlock()
		if closed && !active {
			w.finish()
		}
	}()
	// Revalidate the actual current scope before consuming each fresh callback.
	if e := p.run(ctx, host, func(ops *sdkOps) error {
		for _, spec := range w.specs {
			if e := ops.authorizeDir(spec.Path); e != nil {
				return e
			}
		}
		return nil
	}); e != nil {
		return e
	}
	var event fileEvent
	tick := false
	for {
		select {
		case <-w.stop:
			return nil
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		if e, ok := w.pop(); ok {
			event = e
			break
		}
		due := p.timerDue()
		var timer *time.Timer
		var alarm <-chan time.Time
		if due != nil {
			timer = time.NewTimer(due.Sub(p.machine.Now()))
			alarm = timer.C
		}
		select {
		case <-alarm:
			tick = true
		case <-w.wake:
		case <-w.stop:
			if timer != nil {
				timer.Stop()
			}
			return nil
		case <-ctx.Done():
			if timer != nil {
				timer.Stop()
			}
			return ctx.Err()
		}
		if timer != nil {
			timer.Stop()
		}
		if tick {
			break
		}
	}
	if event.Err != nil {
		return event.Err
	}
	if e := p.run(ctx, host, func(_ *sdkOps) error {
		if tick {
			p.machine.Tick()
			return nil
		}
		switch event.Kind {
		case "created":
			return p.machine.Created(event.Path, event.Directory)
		case "moved":
			return p.machine.Moved(event.Path, event.Dest, event.Mode, event.Directory)
		case "deleted":
			return p.machine.Deleted(event.Path, event.Mode, event.Directory)
		}
		return errors.New("invalid local observer event")
	}); e != nil {
		return e
	}
	w.mu.Lock()
	w.active = false
	closed := w.closed
	w.mu.Unlock()
	released = true
	if !closed {
		return p.submitWatch(ctx, host, w)
	}
	return nil
}

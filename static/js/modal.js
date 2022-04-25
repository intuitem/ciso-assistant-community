function modal() {
    return {
      state: 'CLOSED', // [CLOSED, TRANSITION, OPEN]
      open() {
        this.state = 'TRANSITION'
        setTimeout(() => { this.state = 'OPEN' }, 50)
      },
      close() {
        this.state = 'TRANSITION'
        setTimeout(() => { this.state = 'CLOSED' }, 300)
      },
      isOpen() { return this.state === 'OPEN' },
      isOpening() { return this.state !== 'CLOSED' },
    }
  }
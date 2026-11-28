Component({
    properties: {
      item: {
        type: Object,
        value: {}
      }
    },

    methods: {
      handleTap() {
        this.triggerEvent('needtap', {
          id: this.properties.item.id
        })
      }
    }
  })

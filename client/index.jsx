(function() {
  var AvailableGames = React.createClass({

    getInitialState: function() {
      return {games: []}
    },

    render: function() {
      return (<div id="list-games"><h2>Active Games</h2></div>)
    },

    componentDidMount: function() {
      this.refresh();
      this.timer = setInterval(this.refresh, 2000);
    },

    componentWillUnmount: function() {
      clearInterval(this.timer);
    },

    refresh: function() {
      var self = this;
      $.get('/list', function(r) { self.setState(r); });
    },

    render: function() {
      return (
        <div id="games-list">
          <h2>Available Games</h2>
          <ul>
            { this.state.games.map(function(g) {
              return <li key={g.uuid}><span className="game-uuid">{g.uuid}</span> <span className="game-playerCount">({g.players} players)</span></li>
            }) }
          </ul>
        </div>
      )
    }
  });

  React.render(
    (
      <div>
        <h1>Let's play dominion!</h1>
        <AvailableGames />
      </div>
    ),
    document.getElementById('content')
  );
})();

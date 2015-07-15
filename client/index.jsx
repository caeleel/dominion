(function() {
  var POLLING_PAUSE = 2000;

  var AvailableGames = React.createClass({
    getInitialState: function() { return {games: []} },

    componentDidMount: function() {
      this.refresh();
      this.timer = setInterval(this.refresh, POLLING_PAUSE);
    },

    componentWillUnmount: function() { clearInterval(this.timer); },

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
              return <li key={g.uuid}>
                <span className="game-uuid">{g.uuid}</span> <span className="game-playerCount">({g.players} players)</span>
              </li>
            }) }
          </ul>
        </div>
      )
    }
  });

  var GameCreator = React.createClass({
    submit: function(evt) {
      evt.preventDefault();
      $.post('/create', {}, function(response) {
        console.log(response);
      });
    },

    render: function() {
      return (
        <div id="create-game">
          <h2>New Game</h2>
          <form onSubmit={this.submit}>
            <div><input type="text" name="title" placeholder="My cool game" /></div>
            <div><input type="submit" value="Let's play!" /></div>
          </form>
        </div>
      )
    }
  });

  React.render(
    (
      <div>
        <h1>Let's play dominion!</h1>
        <AvailableGames />
        <GameCreator />
      </div>
    ),
    document.getElementById('content')
  );
})();

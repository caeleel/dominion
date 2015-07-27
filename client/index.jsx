(function() {
  $.ajaxSetup({contentType: 'application/json'});

  var AvailableGames = React.createClass({
    getInitialState: function() { return {games: []} },

    componentDidMount: function() {
      var self = this;
      $.get('/list', function(r) { self.setState(r); });
    },

    handleClick: function(game) {
      this.props.joinFunc(game);
    },

    render: function() {
      var self = this;
      return (
        <div id="games-list">
          <h2>Available Games</h2>
          <ul>
            {this.state.games.map(function(g) {
              return (
                <li key={g.uuid}>
                  <span onClick={self.handleClick.bind(self, g.uuid)} className="game-title">{g.title}</span>
                  <span className="game-playerCount">({g.players} players)</span>
                </li>
              );
            })}
          </ul>
        </div>
      );
    }
  });

  var Card = React.createClass({
    onHover: function() {
      var uuid = this.props.card.uuid;
      $("#expand-info").html($("#" + uuid).html());
    },

    render: function() {
      var card = this.props.card;
      var type = null;

      switch(card.type) {
        case 'Action - Reaction':
          type = 'reaction';
          break;
        case 'Action - Attack':
          type = 'attack';
          break;
        case 'Action - Victory':
          type = 'actionVictory';
          break;
        case 'Action - Duration':
          type = 'duration';
          break;
        default:
          type = card.type.toLowerCase();
      }
      type = "card " + type;

      return (
        <div className="supply-item">
          <div id={card.uuid} className={type} onMouseOver={this.onHover}>
            <div className="header">
              <div className="value">
                {card.value > 0 && '$' + card.value}
              </div>
              <div className="name">
                {card.name}
              </div>
            </div>
            <div className="vp">
              { card.points > 0 &&
                <div className="points">
                  {card.points} VP
                </div>
              }
            </div>
            <div className="footer">
              <div className="cost">
                {card.cost}
              </div>
              <div className="type">
                {card.type}
              </div>
            </div>
            <div className="text">
              {card.text.map(function(line) {
                if(line == '------') {
                  return (
                    <div className="divider"></div>
                  )
                } else {
                  return (
                    <div className="line">{line}</div>
                  )
                }
              })}
            </div>
          </div>
          { this.props.remaining != null &&
            <div className="cards-left">
              { this.props.remaining }
            </div>
          }
        </div>
      );
    }
  });

  var Supply = React.createClass({
    render: function() {
      var cards = this.props.supply.map(function(card_set) {
        return (
          <Card key={card_set.card.uuid} card={card_set.card} remaining={card_set.left} />
        );
      });
      return (
        <div id="supply">
          {cards}
        </div>
      );
    }
  });

  var Hand = React.createClass({
    render: function() {
      var cards = [];
      if (this.props.hand) {
        cards = this.props.hand.map(function(card) {
          return (
              <Card key={card.uuid} card={card} />
          )
        });
      }
      return (
        <div id="hand">
          {cards}
        </div>
      );
    }
  });

  var Game = React.createClass({
    getInitialState: function() {
      return {
        supply: [],
      };
    },

    poll: function() {
      var self = this;
      this.request = $.get('/poll/' + this.props.gid + '?pid=' + this.props.pid + '&uuid=' + this.props.uuid, function(r) {
        self.setState({
          supply: r.state.supply,
        });
        self.poll();
      });
    },

    stat: function() {
      var self = this;
      $.get('/stat/' + this.props.gid + '?pid=' + this.props.pid + '&uuid=' + this.props.uuid, function(r) {
        self.setState({
          supply: r.state.supply,
          hand: r.state.deck.hand,
        });
      });
    },

    componentDidMount: function() {
      this.stat();
      this.poll();
    },

    componentWillUnmount: function() {
      this.request.abort();
    },

    render: function() {
      return (
        <div id="container">
          <div id="card-area">
            <Supply supply={this.state.supply} />
            <div className="breaker"></div>
          </div>
          <div id="expand-info"></div>
          <Hand hand={this.state.hand} />
          <div className="breaker"></div>
        </div>
      );
    }
  });

  var GameCreator = React.createClass({
    join: function(game) {
      game_creator = this;
      $.post('/join/' + game, function(response) {
        game_creator.setState({
          joined: true,
          pid: response.id,
          uuid: response.uuid,
          gid: game,
        });
        game_creator.save();
      });
    },

    submit: function(evt) {
      evt.preventDefault();
      var game_creator = this;
      $.post('/create', JSON.stringify(this.state), function(game) {
        game_creator.join(game.game);
        game_creator.setState({start_key: game.start});
      });
    },

    componentDidMount: function() {
      var session = window.localStorage.getItem('session');
      if (session === null) return;
      session = JSON.parse(session);
      this.setState(session);
    },

    getInitialState: function() {
      return {
        title: 'My cool game!',
        joined: false,
      };
    },

    handleChange: function(event) {
      this.setState({title: event.target.value});
    },

    save: function() {
      var self = this;
      setTimeout(function() {
        window.localStorage['session'] = JSON.stringify(self.state);
      }, 500);
    },

    leaveGame: function() {
      this.setState({joined: false});
      this.save();
    },

    startGame: function() {
      console.log(this.state.start_key);
    },

    render: function() {
      if (this.state.joined) {
        return (
          <div id="game">
            <div id="game-title">
              <span id="game-title-span">{this.state.title}</span>
              <button id="leave-game" onClick={this.leaveGame}>Leave</button>
              { this.state.start_key &&
                <button id="start-game" onClick={this.startGame}>Start</button>
              }
            </div>
            <Game gid={this.state.gid} pid={this.state.pid} uuid={this.state.uuid} />
          </div>
        );
      } else {
        return (
          <div id="game-manager">
            <h1 id="title">Let's play dominion!</h1>
            <AvailableGames joinFunc={this.join} />
            <div id="create-game">
              <h2>New Game</h2>
              <form onSubmit={this.submit}>
                <div><input type="text" name="title" value={this.state.title} onChange={this.handleChange} /></div>
                <div><input type="submit" value="Let's play!" /></div>
              </form>
            </div>
          </div>
        );
      }
    }
  });

  React.render(
    (
      <div>
        <GameCreator />
      </div>
    ),
    document.getElementById('content')
  );
})();

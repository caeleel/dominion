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
                  <span
                    onClick   = {self.handleClick.bind(self, g.uuid)}
                    className = "game-title"
                  >
                    {g.title}
                  </span>
                  <span className="game-playerCount">
                    ({g.players} players)
                  </span>
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

    doCard: function() {
      this.props.callback(this.props.type, this.props.card);
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
          <div
            onClick     = {this.doCard}
            id          = {card.uuid}
            className   = {type}
            onMouseOver = {this.onHover}
          >
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
      var self = this;
      var cards = this.props.supply.map(function(card_set) {
        return (
          <Card
            key       = {card_set.card.uuid}
            callback  = {self.props.callback}
            type      = "supply"
            card      = {card_set.card}
            remaining = {card_set.left}
          />
        );
      });
      return (
        <div id="supply">
          {cards}
        </div>
      );
    }
  });

  var CardList = React.createClass({
    render: function() {
      var cards = [];
      var self = this;
      if (this.props.cards) {
        cards = this.props.cards.map(function(card) {
          return (
              <Card
                key      = {card.uuid}
                callback = {self.props.callback}
                type     = {self.props.name}
                card     = {card}
              />
          )
        });
      }
      return (
        <div id={this.props.name}>
          <div className="cards-inner">
            {cards}
          </div>
        </div>
      );
    }
  });

  var Game = React.createClass({
    getInitialState: function() {
      return {
        supply: [],
        hand: [],
        discard: [],
        in_play: [],
        actions: 1,
        buys: 1,
        money: 0,
        turn: -1,
        phase: "pregame",
        target: "normal",
      };
    },

    doCard: function(type, card) {
      var self = this;
      var pid = this.props.pid;
      var uuid = this.props.uuid;

      if (this.state.target == "normal") {
        if (type != "hand" && type != "supply") return;
        var action = (type == "hand" ? "/play/" : "/buy/");

        $.post(
          '/game/' + this.props.gid + action + card.name + this.loginArgs(),
          '{}',
          function(resp) {
            self.updateState(resp);
          }
        );
      }
    },

    updateState: function(r) {
      if (r.state) {
        this.setState({
          supply: r.state.supply,
          hand: r.state.deck.hand,
          discard: r.state.deck.discard,
          in_play: r.state.deck.in_play,
          actions: r.state.actions,
          buys: r.state.buys,
          money: r.state.money,
          turn: r.state.turn,
          phase: r.state.state,
        });
      }
    },

    loginArgs: function() {
      return '?pid=' + this.props.pid + '&uuid=' + this.props.uuid;
    },

    nextPhase: function() {
      var self = this;
      this.request = $.post(
        '/game/' + this.props.gid + '/next_phase' + this.loginArgs(),
        function(resp) {
          self.updateState(resp);
        }
      );
    },

    poll: function() {
      var self = this;
      this.request = $.get(
        '/poll/' + this.props.gid + this.loginArgs(),
        function(resp) {
          self.updateState(resp);
          self.poll();
        }
      );
    },

    stat: function() {
      var self = this;
      $.get(
        '/stat/' + this.props.gid + this.loginArgs(),
        function(resp) {
          self.updateState(resp);
        }
      );
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
            <Supply supply={this.state.supply} callback={this.doCard}/>
            <div className="breaker"></div>
          </div>
          <div id="expand-info"></div>
          <div id="inplay-popup">
            <div className="popup-bar" id="inplay-bar">
              <img src="client/img/inplay.png" />
            </div>
            <CardList cards={this.state.in_play} callback={this.doCard} name="inplay" />
          </div>
          <div id="discard-popup">
            <div className="popup-bar" id="discard-bar">
              <img src="client/img/trash.png" />
            </div>
            <CardList cards={this.state.discard} callback={this.doCard} name="discard" />
          </div>
          <div id="hand-wrapper">
            <CardList cards={this.state.hand} callback={this.doCard} name="hand" />
          </div>
          <div id="status-window">
            <div id={"n-a-" + this.state.phase} className="status-box">
              <span className="status-label">A</span> {this.state.actions}
            </div>
            <div id={"n-b-" + this.state.phase} className="status-box">
              <span className="status-label">B</span> {this.state.buys}
            </div>
            <div id="n-m" className="status-box">
              <span className="status-label">$</span> {this.state.money}
            </div>
            <div id="next-phase" className="status-box" onClick={this.nextPhase}>&#x25b8;</div>
          </div>
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
      var self = this;
      $.post('/start/' + this.state.gid + '/' + this.state.start_key, function(resp) {
        self.setState({start_key: null});
        self.save();
      });
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
                <div>
                  <input
                    type     = "text"
                    name     = "title"
                    value    = {this.state.title}
                    onChange = {this.handleChange} />
                </div>
                <div>
                  <input type="submit" value="Let's play!" />
                </div>
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
